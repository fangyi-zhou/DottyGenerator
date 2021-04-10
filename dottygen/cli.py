from argparse import ArgumentParser
import typing
import time

from benchmark.apigeneration.counter import Counter
from benchmark.codeline.line_counter import LineCounter
from dottygen.automata import parser as automata_parser
from dottygen.utils import logger, scribble, type_declaration_parser, role_parser
from dottygen.generator import DottyGenerator
from dottygen.generator.merger import Merger
from dottygen.generator.channel_generator import CaseClassGenerator, ChannelGenerator
from dottygen.generator.file_writer import FileWriter, RecurseTypeGenerator
from dottygen.generator.output_generator import OutputGenerator

def parse_arguments(args: typing.List[str]) -> typing.Dict:
    """Prepare command line argument parser and return the parsed arguments
    from the specified 'args'."""

    parser = ArgumentParser()

    parser.add_argument('filename',
                        type=str, help='Path to Scribble protocol')

    parser.add_argument('protocol',
                        type=str, help='Name of protocol')

    parser.add_argument('--output',
                         type=str, help='Output directory for generation', default='/home/dev/effpi_sandbox/src/main/scala')

    parser.add_argument('--single', help='output as a single file', action='store_true')

    parsed_args = parser.parse_args(args)
    return vars(parsed_args)


def main(args: typing.List[str]) -> int:
    """Main entry point, return exit code."""

    parsed_args = parse_arguments(args)

    protocol = parsed_args['protocol']
    output_folder = parsed_args['output']
    scribble_file = parsed_args['filename']
    batch = not parsed_args['single']

    return generate(batch, output_folder, protocol, scribble_file)


def generate(batch, output_folder, protocol, scribble_file, counter=Counter(), line_counter=LineCounter()):
    labels = set()
    channel_list = []
    efsms = {}
    all_roles = role_parser.parse(scribble_file, protocol)

    recurse_generator = RecurseTypeGenerator()
    recurse_generator.setup()

    output_generator = OutputGenerator()

    for role in all_roles:
        counter.set_role(role)
        try:
            message = f'Role {role} : Getting protocol from {scribble_file}'
            with type_declaration_parser.parse(scribble_file) as custom_types:
                start_time = time.time()
                exit_code, output = scribble.get_graph(scribble_file, protocol, role)
                end_time = time.time()
                counter.add_nuscr_time(end_time - start_time)
                if exit_code != 0:
                    logger.FAIL(message)
                    logger.ERROR(output)
                    return exit_code
                logger.SUCCESS(message)
        except (OSError, ValueError) as error:
            logger.ERROR(error)
            return 1

        phase = f'Role {role} : Parse endpoint IR from Scribble output'
        try:
            start_time = time.time()
            efsm = automata_parser.from_data(output)
            end_time = time.time()
            counter.add_efsm_time(end_time - start_time)
            efsms[role] = efsm
            logger.SUCCESS(phase)
        except ValueError as error:
            logger.FAIL(phase)
            logger.ERROR(error)
            return 1

    start_time = time.time()
    merger = Merger(efsms)
    channel_map = merger.merge()
    end_time = time.time()
    counter.add_merge_time(end_time-start_time)

    for role in all_roles:
        counter.set_role(role)
        efsm = efsms[role]
        phase = f'Role {role} : Generating Type from EFSM'
        try:
            other_roles = all_roles - set(role)
            generator = DottyGenerator(efsm=efsm, protocol=protocol, role=role, other_roles=other_roles,
                                       recurse_generator=recurse_generator)
            type, function, label, channels = generator.build(counter)
            output_generator.add_type(role, type)
            output_generator.add_function(role, function)
            channel_list.append((role, channels))
            labels = labels.union(label)
            logger.SUCCESS(phase)
        except (OSError, ValueError) as error:
            logger.FAIL(phase)
            logger.ERROR(error)
            return 1
    phase = f'Writing functions and types into file'
    try:
        # print(counter.get_merge_time())
        # print(counter.get_class_time())
        # print(counter.get_efsm_time())
        # print(counter.get_type_time())
        # print(counter.get_function_time())
        # print(counter.get_nuscr_time())
        #print(counter.get_merge_time() + counter.get_class_time() + counter.get_efsm_time() + counter.get_type_time() + counter.get_function_time() + counter.get_nuscr_time())
        line_counter.add_case_class(labels)
        case_classes = CaseClassGenerator(labels).generate()
        channels_assign = ChannelGenerator(channel_list, channel_map).generate()
        if not batch:
            output_generator.single_output(output_folder, case_classes, channels_assign, protocol)
        else:
            output_generator.batch_output(output_folder, case_classes, channels_assign, protocol, all_roles)
    except (OSError, ValueError) as error:
        logger.FAIL(phase)
        logger.ERROR(error)
        return 1
    return 0