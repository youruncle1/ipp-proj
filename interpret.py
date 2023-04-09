import argparse
import sys
import re
import xml.etree.ElementTree as ET

def argparser():
    parser = argparse.ArgumentParser(
        description="Interpreter for IPPcode23.",
        epilog="At least one of the parameters (--source or --input) must always be specified.",
        add_help=False,
        usage="%(prog)s [--help] [--source=file] [--input=file]"
    )

    parser.add_argument(
        "--help",
        action="store_true",
        dest="help",
        help="Print a script hint to the standard output (does not load any input).",
    )

    parser.add_argument(
        "--source",
        type=str,
        metavar="file",
        help="Input file with XML representation of the source code. Must be specified in the format --source=file.",
    )

    parser.add_argument(
        "--input",
        type=str,
        metavar="file",
        help="File with inputs for the actual interpretation of the specified source code. Must be specified in the format --input=file.",
    )

    args, unknown = parser.parse_known_args()

    if args.help:
        if len(sys.argv) > 2:
            parser.error("help parameter cannot be combined with any other parameter")
            sys.exit(10)
        parser.print_help()
        sys.exit(0)

    if unknown:
        parser.error(f"Unrecognized arguments: {', '.join(unknown)}")

    if not args.source and not args.input:
        parser.error("At least one of the parameters (--source or --input) must always be specified.")

    return args
class Instruction:
    def __init__(self, order, opcode, args):
        self.order = order
        self.opcode = opcode
        self.args = args

class Argument:
    def __init__(self, arg_type, value):
        self.arg_type = arg_type
        self.value = value

class XMLValidator:
    def __init__(self, xml_string):
        try:
            self.root = ET.fromstring(xml_string)
        except ET.ParseError:
            self.root = None
        
        self.valid_opcodes = {
            'CREATEFRAME': 0, 'PUSHFRAME': 0, 'POPFRAME': 0, 'RETURN': 0, 'BREAK': 0,
            'DEFVAR': 1, 'POPS': 1, 'CALL': 1, 'LABEL': 1, 'JUMP': 1, 'PUSHS': 1, 'WRITE': 1, 'EXIT': 1, 'DPRINT': 1,
            'MOVE': 2, 'INT2CHAR': 2, 'NOT': 2, 'STRLEN': 2, 'TYPE': 2, 'READ': 2,
            'ADD': 3, 'SUB': 3, 'MUL': 3, 'IDIV': 3, 'LT': 3, 'GT': 3, 'EQ': 3, 'AND': 3, 'OR': 3, 'STRI2INT': 3, 'CONCAT': 3, 'GETCHAR': 3, 'SETCHAR': 3, 'JUMPIFEQ': 3, 'JUMPIFNEQ': 3
        }
        
        self.valid_argtypes = {
            "var": r"^(LF|TF|GF)@[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$",
            "type": r"^(bool|int|string)$",
            "label": r"^[a-zA-Z\-_$&%*!?][a-zA-Z0-9\-_$&%*!?]*$",
            "nil": r"^nil$",
            "string": r"^([^\\]|\\\d{3})*$",
            "bool": r"^(true|false)$",
            "int": r"^(?:\+|-)?(?:(?!.*_{2})(?!0\d)\d+(?:_\d+)*|0[oO]?[0-7]+(_[0-7]+)*|0[xX][0-9a-fA-F]+(_[0-9a-fA-F]+)*)$"
        }

    def check_header(self):
        if self.root is None:
            return 31, "XML parse error"
        if self.root.tag != "program" or self.root.get("language") != "IPPcode23":
            return 32, "Invalid program header"
        return 0, None

    def parse_instruction(self, xml_instruction):
        order = xml_instruction.get("order")
        if order is None or not order.isdigit() or int(order) < 1:
            return None, 32, f"Invalid order value in Instruction Order {order}"
        order = int(order)

        opcode = xml_instruction.get("opcode").upper()
        if not opcode or opcode not in self.valid_opcodes:
            return None, 32, f"Invalid opcode name '{opcode}' in Instruction Order {order}"
        required_args = self.valid_opcodes[opcode]
        args = []

        arg_tags = {}
        for arg in xml_instruction:
            if not re.match(r'arg[123]$', arg.tag):
                return None, 32, f"Invalid argument tag '{arg.tag}' in Instruction Order {order}"
            arg_index = int(arg.tag[-1])
            if arg_index in arg_tags:
                return None, 32, f"Duplicate argument tag in Instruction Order {order}"
            arg_tags[arg_index] = arg

        if len(arg_tags) != required_args:
            return None, 32, f"Incorrect number of arguments in Instruction Order {order}"

        for i in range(1, len(arg_tags) + 1):
            arg = arg_tags.get(i)
            if arg is None:
                return None, 32, f"Missing argument in Instruction Order {order}"
            arg_type = arg.get("type")

            # Check if arg_type is in valid_argtypes (valid_argtypes)
            if arg_type not in self.valid_argtypes:
                return None, 32, f"Invalid argument type '{arg.type}' in Instruction Order {order}"

            arg_value = arg.text

            # Check if arg_value matches the corresponding regex pattern for the arg_type
            pattern = self.valid_argtypes.get(arg_type)
            if not re.match(pattern, arg_value):
                return None, 32, f"Invalid argument value in Instruction Order {order}"

            args.append(Argument(arg_type, arg_value))

        return Instruction(order, opcode, args), 0, None

    def validate_instructions(self):
        instructions = []
        orders = []

        for xml_instruction in self.root:
            if xml_instruction.tag == "instruction":
                instruction, error_code, error_message = self.parse_instruction(xml_instruction)
                if error_code:
                    return None, error_code, error_message

                if instruction.order in orders:
                    return None, 32, f"Duplicate instruction in Instruction Order {instruction.order}"

                instructions.append(instruction)
                orders.append(instruction.order)
            else:
                return None, 32, f"Invalid element '{xml_instruction.tag}' found"

        instructions.sort(key=lambda instr: instr.order)

        return instructions, 0, None

    def validate(self):
        error_code, error_message = self.check_header()
        if error_code:
            return error_code, error_message

        instructions, error_code, error_message = self.validate_instructions()
        if error_code:
            return error_code, error_message

        return 0, None


def main():
    args = argparser()
    
    if args.source:
        try:
            with open(args.source, "r") as file:
                xml_string = file.read()
        except IOError:
            print(f"Error: Could not read file '{args.source}'", file=sys.stderr)
            sys.exit(10)
    else:
        xml_string = sys.stdin.read()
        
    validator = XMLValidator(xml_string)
    error_code, error_message = validator.validate()

    if error_code:
        print(f"XMLError {error_code}: {error_message}", file=sys.stderr)
        sys.exit(error_code)


if __name__ == "__main__":
    main()