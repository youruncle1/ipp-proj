import argparse
import sys
import re
import xml.etree.ElementTree as ET

def argparser():
    parser = argparse.ArgumentParser(
        description="Interpreter for IPPcode23.",
        epilog="At least one of the parameters (--source or --input) must always be specified.",
        add_help=False,
        usage="interpret.py [--help] [--source=file] [--input=file]"
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
        self.args = sorted(args, key=lambda x: x.order)

class Argument:
    def __init__(self, arg_type, value, order):
        self.arg_type = arg_type
        self.value = value
        self.order = order 

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

        opcode = xml_instruction.get("opcode")
        if not opcode or opcode.upper() not in self.valid_opcodes:
            return None, 32, f"Invalid opcode name '{opcode}' in Instruction Order {order}"
        required_args = self.valid_opcodes[opcode.upper()]
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
            return None, 32, f"Incorrect number of arguments in Instruction Order {order} ({len(arg_tags)}, Expected: {required_args})"

        for i in range(1, len(arg_tags) + 1):
            arg = arg_tags.get(i)
            if arg is None:
                return None, 32, f"Missing argument in Instruction Order {order}"
            arg_type = arg.get("type")

            # Check if arg_type is in valid_argtypes (valid_argtypes)
            if arg_type not in self.valid_argtypes:
                return None, 32, f"Invalid argument type '{arg_type}' in Instruction Order {order}"

            arg_value = arg.text if arg.text is not None else ""

            pattern = self.valid_argtypes.get(arg_type)
            if not re.match(pattern, arg_value):
                return None, 32, f"Invalid argument value '{arg_value}' in Instruction Order {order}"

            args.append(Argument(arg_type, arg_value, i))

        return Instruction(order, opcode, args), 0, None

    def validate_instructions(self):
        instructions = []
        orders = []
        labels = {} 

        for xml_instruction in self.root:
            if xml_instruction.tag == "instruction":
                instruction, error_code, error_message = self.parse_instruction(xml_instruction)
                if error_code:
                    return None, None, error_code, error_message

                if instruction.opcode.upper() == "LABEL":
                    label_name = instruction.args[0].value
                    if label_name in labels:
                        return None, None, 52, f"Duplicate label '{label_name}' in Instruction Order {instruction.order}"
                    labels[label_name] = instruction.order 

                if instruction.order in orders:
                    return None, None, 32, f"Duplicate instruction order in Instruction Order {instruction.order}"

                instructions.append(instruction)
                orders.append(instruction.order)
                #print(f"Instruction Order {instruction.order}: args = {[arg.__dict__ for arg in instruction.args]}")
            else:
                return None, None, 32, f"Invalid element '{xml_instruction.tag}' found"

        instructions.sort(key=lambda instr: instr.order)

        return instructions, labels, 0, None 

    def validate(self):
        error_code, error_message = self.check_header()
        if error_code:
            return error_code, error_message

        instructions, labels, error_code, error_message = self.validate_instructions() 
        if error_code:
            return error_code, error_message

        return 0, None

class IPPInterpreter:
    def __init__(self, instructions, labels):
        self.frames = {
            'GF': {},
            'LF': None,
            'TF': None
        }
        self.frame_stack = []
        self.call_stack = []
        self.data_stack = []
        self.instructions = instructions
        self.labels = labels
        self.current_position = 0
        self.executed_instructions_count = 0

        self.instruction_mapping = {
            'MOVE': self.move,
            'CREATEFRAME': self.create_frame,
            'PUSHFRAME': self.push_frame,
            'POPFRAME': self.pop_frame,
            'DEFVAR': self.def_var,
            'CALL': self.call,
            'RETURN': self.return_instruction,
            'PUSHS': self.pushs,
            'POPS': self.pops,
            'ADD': self.add,
            'SUB': self.sub,
            'MUL': self.mul,
            'IDIV': self.idiv,
            'LT': self.lt_gt_eq,
            'GT': self.lt_gt_eq,
            'EQ': self.lt_gt_eq,
            'AND': self.and_or_not,
            'OR': self.and_or_not,
            'NOT': self.and_or_not,
            'INT2CHAR': self.int2char,
            'STRI2INT': self.stri2int,
            'READ': self.read,
            'WRITE': self.write,
            'CONCAT': self.concat,
            'STRLEN': self.strlen,
            'GETCHAR': self.getchar,
            'SETCHAR': self.setchar,
            'TYPE': self.type_instruction,
            'LABEL': self.label_instruction,
            'JUMP': self.jump_instruction,
            'JUMPIFEQ': self.jumpifeq_instruction,
            'JUMPIFNEQ': self.jumpifneq_instruction,
            'EXIT': self.exit_instruction,
            'DPRINT': self.dprint_instruction,
            'BREAK': self.break_instruction
        }

    def is_variable_identifier(self, value):
        #print(f"is_variable_identifier called with value: {value}, type: {type(value)}")
        frame_prefixes = ["GF@", "LF@", "TF@"]
        return any(value.startswith(prefix) for prefix in frame_prefixes)

    def is_variable_defined(self, var):
    
        frame_name, var_name = var.split('@', 1)
        frame_name = frame_name.upper()
        
        if frame_name == 'GF':
            if not var_name in self.frames[frame_name]:
                return 54
            else:
                return 0
        else:
            if self.frames[frame_name] is None:
                return 55
            if not var_name in self.frames[frame_name]:
                return 54   
        return 0

    def get_operand_values(self, symb1, symb2=None):
        symb_values = []
        symb_types = []
        for symb in [symb1, symb2]:
            if symb is None: #single symb instruction behaviour
                break
            symb_value = symb.value
            symb_type = symb.arg_type
            #print(f"in get_operand symb_value: {symb_value}, symb.value: {symb.value}, symb_type {symb_type}")
            if symb_type == 'var':
                if self.is_variable_identifier(symb_value):
                    frame_name, var_name = symb_value.split('@', 1)
                    frame_name = frame_name.upper()
                    #print(f"frame_name {frame_name}, var_name {var_name}")
                    if self.frames[frame_name] is None:
                        return 55, (None, None), (None, None)  # Access to a non-existent frame
                    
                    if var_name not in self.frames[frame_name]:
                        return 54, (None, None), (None, None)  # variable undefined
                    
                    if self.frames[frame_name][var_name] is None:
                        return 56, (None, None), (None, None)  # variable uninitialized
                    
                    symb_value = self.frames[frame_name][var_name][0]
                    if symb_value is None:
                        return 56, (None, None), (None, None)  # Error: Missing value (in a variable)
                    symb_actual_type = self.frames[frame_name][var_name][1]
                    
                    #print(f"in get_operand symb_value {symb_value}, value type {type(symb_value)}")
                    #print(f"in get_operand symb_actual_type {symb_actual_type}, value type {type(symb_actual_type)}")
                    if symb_actual_type == 'bool':
                        symb_value = self.frames[frame_name][var_name][0] == True
                        #print(f"{symb_value}, {self.frames[frame_name][var_name][0]}")
                    
                    if symb_actual_type == 'int':
                        symb_value = self.parse_int(str(self.frames[frame_name][var_name][0]))
                    
                    #print(f"in get_operand symb_value AFTER {symb_value}")
                else:
                    return 53, (None, None), (None, None)  # wrong type

            elif symb_type == 'int':
                symb_value = self.parse_int(symb_value)
                symb_actual_type = 'int'
                if symb_value is None:
                    return 53, (None, None), (None, None)  # wrong type

            elif symb_type == 'bool':
                symb_value = symb_value.lower() == 'true'
                symb_actual_type = 'bool'

            elif symb_type == 'string':
                symb_value = symb_value.encode('utf-8').decode('unicode_escape')
                symb_actual_type = 'string'
            
            elif symb_type == 'nil':
                symb_value = 'nil'
                symb_actual_type = 'nil'

            else:
                return 53, (None, None), (None, None)  # wrong type
            
            symb_values.append(symb_value)
            symb_types.append(symb_actual_type)

        if symb2 is None:
            symb_values.append(None)
            symb_types.append(None)
            return 0, symb_values, symb_types
        
        return 0, symb_values, symb_types
    
    def store_result(self, var, result):
        frame_name, variable_name = var.value.split('@', 1)
        frame_name = frame_name.upper()

        if frame_name not in self.frames:
            return 54  # Access to a non-existent variable (frame exists)
        self.frames[frame_name][variable_name] = (result[0], result[1])
        #print(f"self.frames[{frame_name}][{variable_name}] = ({result[0], result[1]})")
        return 0 


    def parse_int(self, value):
        #print(f"parse_int called with value: {value}, type: {type(value)}")
        try:
            if value.startswith("0x") or value.startswith("0X"):
                return int(value, 16)  # hexadecimal
            elif value.startswith("0o") or value.startswith("0O"):
                return int(value, 8)  # octal
            else:
                return int(value)  # decimal
        except ValueError:
            return None

    def move(self, var, symb):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code
        #print(f"in move symb.arg_type = {symb.arg_type}")
        error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)  
        if error_code != 0:
            return error_code

        return self.store_result(var, (symb_value, symb_type))

    def create_frame(self):
        self.frames['TF'] = {}
        return 0  
    
    def push_frame(self):
        if self.frames['TF'] is None:
            return 55  # Accessing undefined frame

        self.frame_stack.append(self.frames['TF'])
        self.frames['LF'] = self.frames['TF']
        self.frames['TF'] = None
        return 0  
    
    def pop_frame(self):
        if self.frames['LF'] is None:
            return 55  # Accessing undefined frame

        self.frames['TF'] = self.frames['LF']
        self.frame_stack.pop()
        if len(self.frame_stack) > 0:
            self.frames['LF'] = self.frame_stack[-1]
        else:
            self.frames['LF'] = None

        return 0 

    def def_var(self, arg):
        #print(f"Inside def_var method with arg: {arg}")
        variable = arg.value

        frame, var_name = variable.split('@')
        if frame not in self.frames or self.frames[frame] is None:
            return 55  # Accessing undefined frame

        if var_name in self.frames[frame]:
            return 52  # Redefining existing variable

        self.frames[frame][var_name] = None
        return 0 
    
    def call(self, label):
        if label not in self.labels:
            return 52  # Undefined label

        self.call_stack.append(self.current_instruction_index + 1)
        self.current_instruction_index = self.labels[label]

        return 0  

    def return_instruction(self):
        if len(self.call_stack) == 0:
            return 56  # Empty call stack

        self.current_instruction_index = self.call_stack.pop()
        return 0 
    
    def pushs(self, symb):
        error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
        if error_code != 0:
            return error_code
        self.data_stack.append((symb_value, symb_type))
        return 0

    def pops(self, var):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code
        
        if len(self.data_stack) == 0:
            return 56  # Empty data stack

        symb_value, symb_type = self.data_stack.pop()
        return self.store_result(var, (symb_value, symb_type))

    def add(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code
        
        #is this needed anymore???
        if (symb1.arg_type != 'int' and symb1.arg_type !='var') or (symb2.arg_type != 'int' and symb2.arg_type !='var'):
            return 53 # wrong type
        
        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'int' or symb2_type != 'int':
            return 53 # wrong type
        
        #print(f"symb1 {symb1_value}, symb1_type: {symb1_type}, {type(symb1_value)}")
        #print(f"symb2 {symb2_value}, symb1_type: {symb2_type}, {type(symb2_value)}")
        result = (symb1_value + symb2_value, 'int')
        return self.store_result(var, result)

    def sub(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code
        
        if (symb1.arg_type != 'int' and symb1.arg_type !='var') or (symb2.arg_type != 'int' and symb2.arg_type !='var'):
            return 53 # wrong type
        
        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'int' or symb2_type != 'int':
            return 53 # wrong type

        result = (symb1_value - symb2_value, 'int')
        return self.store_result(var, result)

    def mul(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code
        
        if (symb1.arg_type != 'int' and symb1.arg_type !='var') or (symb2.arg_type != 'int' and symb2.arg_type !='var'):
            return 53 # wrong type
        
        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'int' or symb2_type != 'int':
            return 53 # wrong type
        
        result = (symb1_value * symb2_value, 'int')
        return self.store_result(var, result)

    def idiv(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code
        
        if (symb1.arg_type != 'int' and symb1.arg_type !='var') or (symb2.arg_type != 'int' and symb2.arg_type !='var'):
            return 53 # wrong type
        
        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'int' or symb2_type != 'int':
            return 53 # wrong type
        
        if symb2_value == 0:
            return 57 # bad operand type: division by zero
        result = (symb1_value // symb2_value, 'int')
        return self.store_result(var, result)
    
    def lt_gt_eq(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb1.arg_type not in ('int', 'bool', 'string', 'nil', 'var') or symb2.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type

        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code

        if symb1_type != symb2_type and (symb1_type != 'nil' and symb2_type != 'nil'):
            return 53 # wrong type

        opcode = self.instructions[self.current_position].opcode.upper()

        if opcode == 'EQ':
            if symb1_type == 'nil' or symb2_type == 'nil':
                result = symb1_type == symb2_type
            else:
                result = symb1_value == symb2_value
        elif opcode in ('LT', 'GT'):
            if symb1_type == 'nil' or symb2_type == 'nil':
                return 53 # wrong type

            if opcode == 'LT':
                result = symb1_value < symb2_value
            else:
                result = symb1_value > symb2_value
        else:
            return 32  # Invalid opcode

        return self.store_result(var, (result, 'bool'))

    def and_or_not(self, var, symb1, symb2=None):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if (symb1.arg_type != 'bool' and symb1.arg_type != 'var') or (symb2 is not None and symb2.arg_type != 'bool' and symb2.arg_type != 'var'):
            return 53 # wrong type
        
        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        #print(f"(symb1_value, symb2_value), (symb1_type, symb2_type) = ({symb1_value},{symb2_value}), ({symb1_type}, {symb2_type})")
        #print(f"type symb1_val {type(symb1_value),}, {type(symb1_type)}")
        opcode = self.instructions[self.current_position].opcode.upper()
        
        if opcode == 'AND':
            if symb2_value is None:
                return 53 
            if symb1_type != 'bool' or symb1_type != 'bool':
                return 53
            #print(f"before and {symb1_value}, {symb2_value}")
            result = symb1_value and symb2_value
            #print(f"after and {symb1_value}, {symb2_value}")
        elif opcode == 'OR':
            if symb2_value is None:
                return 53 
            if symb1_type != 'bool' or symb1_type != 'bool':
                return 53
            result = symb1_value or symb2_value
        elif opcode == 'NOT':
            if symb1_type != 'bool':
                return 53 
            #print(f"debug: not {symb1_value}: {not symb1_value}")
            result = not symb1_value
            #print(f"result of not symb1_value {result}")
        else:
            return 32  # Invalid opcode
        
        result = (result, 'bool')
        return self.store_result(var, result)

    def int2char(self, var, symb):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type
        
        error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)  
        if error_code != 0:
            return error_code
        
        if symb_type != 'int':
            return 53 # wrong type

        try:
            char = chr(symb_value)
        except ValueError:
            return 58  # Invalid Unicode val

        return self.store_result(var, (char, 'string'))

    def stri2int(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb1.arg_type not in ('int', 'bool', 'string', 'nil', 'var') or symb2.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type

        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'string' or symb2_type != 'int':
            return 53 # wrong type

        if symb2_value < 0 or symb2_value >= len(symb1_value):
            return 58  # invalid string operation: indexing outside the given string

        char = symb1_value[symb2_value]
        return self.store_result(var, (ord(char), 'int'))

    def read(self, var, data_type):
        input_value = input()

        try:
            if data_type == 'int':
                converted_value = int(input_value)
            elif data_type == 'string':
                converted_value = str(input_value)
            elif data_type == 'bool':
                converted_value = input_value.lower() == 'true'
            else:
                return 53  # Error: Invalid data type
        except ValueError:
            converted_value = None  # Store nil@nil in case of incorrect input

        frame, variable_name = var.split('@', 1)
        self.frames[frame][variable_name] = converted_value

        return 0  # Success

    def write(self, symb):
    
        error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)  
        if error_code != 0:
            return error_code
        
        opcode = self.instructions[self.current_position-1].opcode.upper()
        
        #print(f"value {symb_value}, opcode {opcode}, {self.instructions[self.current_position-1].opcode.upper() == 'TYPE'} ")
        if symb_type == 'bool':
            output_value = 'true' if symb_value else 'false'
        elif symb_value is None or (symb_value == 'nil' and self.instructions[self.current_position-1].opcode.upper() != 'TYPE'):
            output_value = ''
        else:
            output_value = str(symb_value)

        print(output_value, end='')
        return 0 

    def concat(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb1.arg_type not in ('int', 'bool', 'string', 'nil', 'var') or symb2.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type

        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'string' or symb2_type != 'string':
            return 53 # wrong type

        result = symb1_value + symb2_value
        return self.store_result(var, (result, 'string'))

    def strlen(self, var, symb):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type

        error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None) 
        if error_code != 0:
            return error_code
        if symb_type != 'string':
            return 53 # wrong type

        string_length = len(symb_value)
        return self.store_result(var, (string_length, 'int'))

    def getchar(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb1.arg_type not in ('int', 'bool', 'string', 'nil', 'var') or symb2.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type

        error_code, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code
        if symb1_type != 'string' or symb2_type != 'int':
            return 53 # wrong type

        if symb2_value < 0 or symb2_value >= len(symb1_value):
            return 58 # invalid string operation

        character = symb1_value[symb2_value]
        return self.store_result(var, (character, 'string'))

    def setchar(self, var, symb1, symb2):
        pass
    '''
        def setchar(self, var, symb1, symb2):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb1.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53
        if symb2.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53

        error_code, var_value, var_type = self.get_operand_value(var)
        if error_code != 0:
            return error_code
        if var_type != 'string':
            return 53

        error_code, symb1_value, symb1_type = self.get_operand_value(symb1)
        if error_code != 0:
            return error_code
        if symb1_type != 'int':
            return 53

        error_code, symb2_value, symb2_type = self.get_operand_value(symb2)
        if error_code != 0:
            return error_code
        if symb2_type != 'string' or len(symb2_value) == 0:
            return 53

        if symb1_value < 0 or symb1_value >= len(var_value):
            return 58

        modified_string = var_value[:symb1_value] + symb2_value[0] + var_value[symb1_value + 1:]
        return self.store_result(var, (modified_string, 'string'))
    '''
    def type_instruction(self, var, symb):
        error_code = self.is_variable_defined(var.value)
        if error_code:
            return error_code

        if symb.arg_type not in ('int', 'bool', 'string', 'nil', 'var'):
            return 53 # wrong type

        symb_value, symb_type = None, None
        if symb.arg_type == 'var':
            error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
            if error_code == 56:  # Uninitialized variable
                symb_type = ''
            elif error_code != 0:
                return error_code
        else:
            symb_type = symb.arg_type

        return self.store_result(var, (symb_type, 'string'))
    
    def label_instruction(self, label):
        if label in self.labels:
            return 52  #duplicate label
        self.labels[label] = self.current_instruction_index
        return 0 

    def jump_instruction(self, label):
        if label not in self.labels:
            return 52  # Error: nonexistent label
        self.current_instruction_index = self.labels[label]
        return 0  # Success

    def jumpifeq_instruction(self, label, symb1, symb2):
        if (type(symb1) != type(symb2)) and (symb1 is not None) and (symb2 is not None):
            return 53  # Error: different types
        if symb1 == symb2:
            return self.jump_instruction(label)
        return 0  # Success
    
    def jumpifneq_instruction(self, label, symb1, symb2):
        if (type(symb1) != type(symb2)) and (symb1 is not None) and (symb2 is not None):
            return 53  # Error: different types
        if symb1 != symb2:
            return self.jump_instruction(label)
        return 0  

    def exit_instruction(self, symb):
        error_code, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
        if error_code != 0:
            return error_code
        if symb_type != 'int':
            return 53 #wrong type
        if 0 <= symb_value <= 49:
            sys.exit(symb_value)
        return 57 #wrong exit code
    
    def dprint_instruction(self, symb):
        print(symb, file=sys.stderr)
        return 0 

    def break_instruction(self):
        print(f"Position in code: {self.current_position}", file=sys.stderr)
        print(f"Global frame: {self.frames['GF']}", file=sys.stderr)
        print(f"Local frame: {self.frames['LF']}", file=sys.stderr)
        print(f"Temporary frame: {self.frames['TF']}", file=sys.stderr)
        print(f"Number of executed instructions: {self.executed_instructions_count}", file=sys.stderr)
        return 0 
    
    def execute_instructions(self):

        while self.current_position < len(self.instructions):
            instruction = self.instructions[self.current_position]

            # Get instruction and its arguments
            instr_name = instruction.opcode.upper()
            instr_name = instr_name.strip()
            args = instruction.args

            #print(f"Instruction name: {instr_name}")
            #print(f"Instruction args: {[str(arg.value) for arg in args]}")

            try:
                # instruction mapping
                if instr_name in self.instruction_mapping:
                    method = self.instruction_mapping[instr_name]
                    # Unpack the args to method
                    result = method(*args)
                else:
                    raise KeyError(f"Invalid instruction name: {instr_name}")

                if result != 0:
                    #print(f"Error code {result} occurred.")
                    return result

                self.executed_instructions_count += 1
                self.current_position += 1
            except Exception as e:
                #print(f"Error occurred: {e}")
                return e
            if 0 < result < 49:
                break

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
        print(f"Error {error_code}: {error_message}", file=sys.stderr)
        exit(error_code)

    instructions, labels, error_code, error_message = validator.validate_instructions()  
    if error_code:
        print(f"Error {error_code}: {error_message}", file=sys.stderr)
        exit(error_code)

    interpreter = IPPInterpreter(instructions, labels) 
    error_code = interpreter.execute_instructions()
    sys.exit(error_code) 

if __name__ == "__main__":
    main()