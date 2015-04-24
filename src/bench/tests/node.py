import bench.exc
import bench.util
import jinja2
import logging
import os
import pkg_resources
import re


TEMPLATE = jinja2.Template(
    pkg_resources.resource_string(__name__, 'node.job'),
    keep_trailing_newline=True,
)

STREAM_P_T = r'^{0}: *([0-9\.]+) +([0-9\.]+) +([0-9\.]+) +([0-9\.]+) *$'
STREAM_COPY_P = re.compile(STREAM_P_T.format('Copy'), flags=re.MULTILINE)
STREAM_SCALE_P = re.compile(STREAM_P_T.format('Scale'), flags=re.MULTILINE)
STREAM_ADD_P = re.compile(STREAM_P_T.format('Add'), flags=re.MULTILINE)
STREAM_TRIAD_P = re.compile(STREAM_P_T.format('Triad'), flags=re.MULTILINE)


logger = logging.getLogger(__name__)


def generate(nodes, prefix):
    tests_dir = os.path.join(prefix, 'tests')
    for node in nodes:
        test_dir = os.path.join(tests_dir, node)
        bench.util.mkdir_p(test_dir)

        script_file = os.path.join(test_dir, '{0}.job'.format(node))
        with open(script_file, 'w') as fp:
            fp.write(TEMPLATE.render(
                node_name = node,
            ))

        node_list_file = os.path.join(test_dir, 'node_list')
        with open(node_list_file, 'w') as fp:
            fp.write('{0}\n'.format(node))


def process(nodes, prefix):
    bad_nodes = set()
    good_nodes = set()
    tests_dir = os.path.join(prefix, 'tests')
    for node in os.listdir(tests_dir):
        try:
            with open(os.path.join(tests_dir, node, 'stream.out')) as fp:
                stream_output = fp.read()
        except IOError as ex:
            logger.warn('{0}: {1}:'.format(node, ex))
            continue
        try:
            stream_data = parse_stream(stream_output)
        except bench.exc.ParseError as ex:
            logger.warn('{0}: {1}:'.format(node, ex))
            continue
        stream_passed = process_stream(stream_data)

        try:
            with open(os.path.join(tests_dir, node, 'linpack.out')) as fp:
                linpack_output = fp.read()
        except IOError as ex:
            logger.warn('{0}: {1}:'.format(node, ex))
            continue
        try:
            linpack_data = parse_linpack(linpack_output)
        except bench.exc.ParseError as ex:
            logger.warn('{0}: {1}:'.format(node, ex))
            continue
        linpack_passed = process_linpack(linpack_data)

        if stream_passed and linpack_passed:
            good_nodes.add(node)
        else:
            bad_nodes.add(node)

    tested = good_nodes | bad_nodes
    not_tested = set(nodes) - tested
    return {
        'not_tested': not_tested,
        'bad_nodes': bad_nodes,
        'good_nodes': good_nodes,
    }


def parse_stream(output):
    copy_match = STREAM_COPY_P.search(output)
    if not copy_match:
        raise bench.exc.ParseError('stream: missing copy')
    copy = float(copy_match.group(1))

    scale_match = STREAM_SCALE_P.search(output)
    if not scale_match:
        raise bench.exc.ParseError('stream: missing scale')
    scale = float(scale_match.group(1))

    add_match = STREAM_ADD_P.search(output)
    if not add_match:
        raise bench.exc.ParseError('stream: missing add')
    add = float(add_match.group(1))

    triad_match = STREAM_TRIAD_P.search(output)
    if not triad_match:
        raise bench.exc.ParseError('stream: missing triad')
    triad = float(triad_match.group(1))

    return (copy, scale, add, triad)


def parse_linpack(output):
    output = output.splitlines()

    # Find the start of the performance summary
    for i, line in enumerate(output):
        if line.startswith('Performance Summary'):
            performance_summary = i
            break
    else:
        raise bench.exc.ParseError('linpack: missing performance summary')

    # Find the performance summary header
    for i, line in enumerate(output[performance_summary+1:]):
        if line.startswith('Size'):
            header = performance_summary + i + 1
            break
    else:
        raise bench.exc.ParseError('linpack: missing performance summary header')

    data = {}
    for line in output[header+1:]:
        if line:
            size, lda, alignment, average, maximal = line.split()
            key = (int(size), int(lda), int(alignment))
            data[key] = float(average)
        else:
            break
    return data


def process_stream(
        data,
        expected_copy = 26500.0,
        expected_scale = 40000.0,
        expected_add = 41500.0,
        expected_triad = 42000.0,
        tolerance = .1,
):
    copy, scale, add, triad = data
    required = 1.0 - tolerance

    if copy < required * expected_copy:
        return False
    elif scale < required * expected_scale:
        return False
    elif add < required * expected_add:
        return False
    elif triad < required * expected_triad:
        return False
    else:
        return True


def process_linpack(
        data,
        expected_averages = {
            (5000, 5000, 4): 105.0,
            (10000, 10000, 4): 114.0,
            (20000, 20000, 4): 121.0,
            (25000, 25000, 4): 122.0,
        },
        tolerance = .1,
):
    required = 1.0 - tolerance

    for key, expected_average in expected_averages.iteritems():
        if key not in data or data[key] < required * expected_average:
            return False
    else:
        return True
