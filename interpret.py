import argparse
import sys
import re
import xml.etree.ElementTree as ET

# parses command-line arguments
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

    args, invalid = parser.parse_known_args()

    if args.help:
        if len(sys.argv) > 2:
            parser.error("help parameter cannot be combined with any other parameter")
            sys.exit(10)
        parser.print_help()
        sys.exit(0)

    if invalid:
        parser.error(f"Unrecognized arguments: {', '.join(invalid)}")

    if not args.source and not args.input:
        parser.error("At least one of the parameters (--source or --input) must always be specified.")

    return args

# replaces unicode escape sequences to ascii (e.g. \035 -> #)
def replace_escapeSequences(match):
    return chr(int(match.group(0)[1:]))

## class Instruction stores instruction's order, OPCODE and it's arguments as objects of class Argument
class Instruction:
    def __init__(self, order, opcode, args):
        self.order = order
        self.opcode = opcode
        self.args = sorted(args, key=lambda x: x.order)

## class Argument stores argument's datatype, value and it's order in instruction
class Argument:
    def __init__(self, arg_type, value, order):
        self.arg_type = arg_type
        self.value = value
        self.order = order 

## class XMLValidator validates an IPPcode23 program formatted in XML.
class XMLParser:
    def __init__(self, xml_string):
        # Parse the xml_string using xml.etree.ElementTree and store to root attribute
        try:
            self.root = ET.fromstring(xml_string)
        except ET.ParseError:
            self.root = None
        # valid opcodes : required number of arguments 
        self.valid_opcodes = {
            'CREATEFRAME': 0, 'PUSHFRAME': 0, 'POPFRAME': 0, 'RETURN': 0, 'BREAK': 0,
            'DEFVAR': 1, 'POPS': 1, 'CALL': 1, 'LABEL': 1, 'JUMP': 1, 'PUSHS': 1, 'WRITE': 1, 'EXIT': 1, 'DPRINT': 1,
            'MOVE': 2, 'INT2CHAR': 2, 'NOT': 2, 'STRLEN': 2, 'TYPE': 2, 'READ': 2,
            'ADD': 3, 'SUB': 3, 'MUL': 3, 'IDIV': 3, 'LT': 3, 'GT': 3, 'EQ': 3, 'AND': 3, 'OR': 3, 'STRI2INT': 3, 'CONCAT': 3, 'GETCHAR': 3, 'SETCHAR': 3, 'JUMPIFEQ': 3, 'JUMPIFNEQ': 3
        }
        
        # regex patterns for validating argument types
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
        # check if XML parsed successfully and then validate header
        if self.root is None:
            return 31, "XML parse error"
        if self.root.tag != "program" or self.root.get("language") != "IPPcode23":
            return 32, "Invalid program header"
        return 0, None

    def parse_instruction(self, xml_instruction):
        # Validate the order attribute of the instruction element
        order = xml_instruction.get("order")
        if order is None or not order.isdigit() or int(order) < 1:
            return None, 32, f"Invalid order value in Instruction Order {order}"
        order = int(order)

        # Validate the opcode attribute of the instruction element
        opcode = xml_instruction.get("opcode")
        if not opcode or opcode.upper() not in self.valid_opcodes:
            return None, 32, f"Invalid opcode name '{opcode}' in Instruction Order {order}"
        required_args = self.valid_opcodes[opcode.upper()]
        args = []

        # Check tags and collect arguments of the instruction
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

        # Validate each argument's type and value
        for i in range(1, len(arg_tags) + 1):
            arg = arg_tags.get(i)
            if arg is None:
                return None, 32, f"Missing argument in Instruction Order {order}"
            arg_type = arg.get("type")

            # Check if arg_type is in valid_argtypes
            if arg_type not in self.valid_argtypes:
                return None, 32, f"Invalid argument type '{arg_type}' in Instruction Order {order}"

            arg_value = arg.text if arg.text is not None else ""

            # Match pattern for given argument type
            pattern = self.valid_argtypes.get(arg_type)
            if not re.match(pattern, arg_value):
                return None, 32, f"Invalid argument value '{arg_value}' in Instruction Order {order}"

            args.append(Argument(arg_type, arg_value, i))

        return Instruction(order, opcode, args), 0, None

    def validate_instructions(self):
        instructions = []
        orders = []
        labels = {} 

        # Iterate through each child element of the root element in XML tree
        for xml_instruction in self.root:
            if xml_instruction.tag == "instruction":
                # Validate the instruction element and its arguments
                instruction, error_code, error_message = self.parse_instruction(xml_instruction)
                if error_code:
                    return None, None, error_code, error_message

                # If the instruction is LABEL, store it in the labels dictionary and check for duplicate labals
                if instruction.opcode.upper() == "LABEL":
                    label_name = instruction.args[0].value
                    if label_name in labels:
                        return None, None, 52, f"Duplicate label '{label_name}' in Instruction Order {instruction.order}"
                    labels[label_name] = instruction.order 

                # Check for duplicate instruction orders
                if instruction.order in orders:
                    return None, None, 32, f"Duplicate instruction order in Instruction Order {instruction.order}"

                instructions.append(instruction)
                orders.append(instruction.order)
                
            else:
                return None, None, 32, f"Invalid element '{xml_instruction.tag}' found"

        # sort instructions by order for the interpreter
        instructions.sort(key=lambda instr: instr.order)

        return instructions, labels, 0, None 

    def validate(self):
        # Check the header
        error_code, error_message = self.check_header()
        if error_code:
            return error_code, error_message

        # Validate instructions and their arguments
        instructions, labels, error_code, error_message = self.validate_instructions() 
        if error_code:
            return error_code, error_message

        return 0, None


class IPPInterpreter:
    def __init__(self, instructions, labels, input_lines=None):
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
        self.current_position = 0  # current position in instructions list
        self.executed_instructions_count = 0 # intented for debug instruction BREAK
        
        # set input 
        if input_lines is None:
            self.input_lines = []
        else:
            self.input_lines = input_lines
        self.input_line_index = 0

        # map each instruction to it's method for self.execute_instructions
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
            'ADD': self.add_sub_mul_idiv,
            'SUB': self.add_sub_mul_idiv,
            'MUL': self.add_sub_mul_idiv,
            'IDIV': self.add_sub_mul_idiv,
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
            'TYPE': self.type,
            'LABEL': self.label,
            'JUMP': self.jump,
            'JUMPIFEQ': self.jumpif,
            'JUMPIFNEQ': self.jumpif,
            'EXIT': self.exit,
            'DPRINT': self.dprint,
            'BREAK': self.break_instruction
        }

    # Check if a variable is defined.
    def is_variable_defined(self, var):
        frame_name, var_name = var.split('@', 1)
        frame_name = frame_name.upper()

        # Check if the variable exists in the Global Frame (GF)
        if frame_name == 'GF':
            if not var_name in self.frames[frame_name]:
                return 54, f"Access to a non-existent variable '{var_name}' in Frame 'GF'"
            else:
                return 0, ""
        else:
            # Check if the Local Frame (LF) or Temporary Frame (TF) exists
            if self.frames[frame_name] is None:
                return 55, f"Accessing '{var_name}' in Frame '{frame_name}', '{frame_name}' does not exist"
            
            # Check if the variable exists in the Local Frame (LF) or Temporary Frame (TF)
            if not var_name in self.frames[frame_name]:
                return 54, f"Access to a non-existent variable '{var_name}' in Frame '{frame_name}'"
        return 0, ""

    # Get the values of the given operands.
    def get_operand_values(self, symb1, symb2=None):
        symb_values = []
        symb_types = []
        for symb in [symb1, symb2]:
            if symb is None:  # single argument instruction behaviour
                break
            symb_value = symb.value
            symb_type = symb.arg_type

            # Check if argument is a variable, then find value and datatype of the variable
            if symb_type == 'var':
                frame_prefixes = ["GF@", "LF@", "TF@"]
                # Check if a value is a valid variable identifier
                if any(symb_value.startswith(prefix) for prefix in frame_prefixes):
                    frame_name, var_name = symb_value.split('@', 1)
                    frame_name = frame_name.upper()

                     # Check if the frame exists
                    if self.frames[frame_name] is None:
                        return 55, f"Accessing '{var_name}' in Frame '{frame_name}', '{frame_name}' does not exist", (None, None), (None, None)

                    # Check if the variable exists in frame
                    if var_name not in self.frames[frame_name]:
                        return 54, f"Accessing to a non-existent variable '{var_name}' in Frame '{frame_name}'", (None, None), (None, None)

                    # Check if the variable has a value
                    if self.frames[frame_name][var_name] is None:
                        return 56, f"Missing value in variable '{var_name}' in Frame '{frame_name}'", (None, None), (None, None)

                    # Get the value and type
                    symb_value = self.frames[frame_name][var_name][0]
                    if symb_value is None:
                        return 56, f"Missing value in variable '{var_name}' in Frame '{frame_name}'", (None, None), (None, None)
                    symb_actual_type = self.frames[frame_name][var_name][1]
                    
                    # Convert values for storing for datatypes bool/int/string
                    if symb_actual_type == 'bool':
                        symb_value = self.frames[frame_name][var_name][0] == True
                    
                    if symb_actual_type == 'int':
                        symb_value = self.parse_int(str(self.frames[frame_name][var_name][0]))
                        
                    if symb_actual_type == 'string':
                        pattern = r'\\[0-9]{3}'
                        symb_value = re.sub(pattern, replace_escapeSequences, self.frames[frame_name][var_name][0])
    
                else:
                    return 53, "Wrong operand types", (None, None), (None, None)
            
            #Convert values for storing for each datatype
            elif symb_type == 'int':
                symb_value = self.parse_int(symb_value)
                symb_actual_type = 'int'
                if symb_value is None:
                    return 53, "Wrong operand types", (None, None), (None, None)  # wrong type

            elif symb_type == 'bool':
                symb_value = symb_value.lower() == 'true'
                symb_actual_type = 'bool'

            elif symb_type == 'string':
                pattern = r'\\[0-9]{3}'
                symb_value = re.sub(pattern, replace_escapeSequences, symb_value)
                symb_actual_type = 'string'
            
            elif symb_type == 'nil':
                symb_value = 'nil'
                symb_actual_type = 'nil'

            else:
                return 53, "Wrong operand types", (None, None), (None, None)
            
            symb_values.append(symb_value)
            symb_types.append(symb_actual_type)

        # single argument instruction behaviour
        if symb2 is None:
            symb_values.append(None)
            symb_types.append(None)
            return 0, "", symb_values, symb_types
        
        return 0, "", symb_values, symb_types
    
    # Store result of instruction into variable
    def store_result(self, var, result):
        frame_name, variable_name = var.value.split('@', 1)
        frame_name = frame_name.upper()

        # Check if the frame name is valid (exists in self.frames)
        if frame_name not in self.frames:
            return 54, f"Accessing '{variable_name}' in Frame '{frame_name}', '{frame_name}' does not exist"
        
        # Store the result (value and value type) in the specified variable within the frame
        self.frames[frame_name][variable_name] = (result[0], result[1])
        
        return 0, ""

    # parse string and check for type of integer, return integer or None if it's not one
    def parse_int(self, value):
        try:
            if value.startswith("0x") or value.startswith("0X"):
                return int(value, 16)  # hexadecimal
            elif value.startswith("0o") or value.startswith("0O"):
                return int(value, 8)  # octal
            else:
                return int(value)  # decimal
        except ValueError:
            return None

    ########### INSTRUCTIONS ###########

    def move(self, var, symb):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message
        
        # Store the result in the destination variable
        error_code, error_message = self.store_result(var, (symb_value, symb_type))
        return error_code, error_message

    def create_frame(self):
        # Create a new temporary frame (TF)
        self.frames['TF'] = {}
        return 0, ""

    def push_frame(self):
        # Check if the temporary frame (TF) is defined
        if self.frames['TF'] is None:
            return 55, "Push to undefined frame (TF)"

        # Push the temporary frame (TF) onto the frame stack and set it as the local frame (LF)
        self.frame_stack.append(self.frames['TF'])
        self.frames['LF'] = self.frames['TF']
        self.frames['TF'] = None
        return 0, ""

    def pop_frame(self):
        # Check if the local frame (LF) is defined
        if self.frames['LF'] is None:
            return 55, "Pop from undefined frame (LF)"

        # Pop the local frame (LF) from the frame stack and set the temporary frame (TF) to the popped frame
        self.frames['TF'] = self.frames['LF']
        self.frame_stack.pop()
        if len(self.frame_stack) > 0:
            self.frames['LF'] = self.frame_stack[-1]
        else:
            self.frames['LF'] = None

        return 0, ""

    def def_var(self, arg):
        variable = arg.value
        
        # Check if the frame exists
        frame_name, var_name = variable.split('@')
        if frame_name not in self.frames or self.frames[frame_name] is None:
            return 55, f"Accessing '{var_name}' in Frame '{frame_name}', '{frame_name}' does not exist"

        # Check if the variable is already defined in the frame
        if var_name in self.frames[frame_name]:
            return 52, f"Redefining existing variable {var_name} in Frame {frame_name}"

        # Define the variable in the frame
        self.frames[frame_name][var_name] = None
        return 0, ""

    def call(self, label):
        # Check if the label exists
        if label.value not in self.labels:
            return 52, f"Call to Undefined label '{label.value}'"

        # Save the current position on the call stack and jump to the label
        self.call_stack.append(self.current_position)
        return self.jump(label)

    def return_instruction(self):
         # Check if the call stack is empty
        if len(self.call_stack) == 0:
            return 56, "Return: Empty call stack"

        # Pop the saved position from the call stack and set the current position
        self.current_position = self.call_stack.pop()
        return 0, ""

    def pushs(self, symb):
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message
        
        # Push the value and type onto the data stack
        self.data_stack.append((symb_value, symb_type))
        return 0, ""

    def pops(self, var):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Check if the data stack is empty
        if len(self.data_stack) == 0:
            return 56, "Pops: Empty data stack"

        # Pop the value and type from the data stack
        symb_value, symb_type = self.data_stack.pop()
        
        # Store the result in the destination variable
        error_code, error_message = self.store_result(var, (symb_value, symb_type))
        return error_code, error_message

    def add_sub_mul_idiv(self, var, symb1, symb2):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Check if both operands are integers
        if symb1_type != 'int' or symb2_type != 'int':
            return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

        # Get the current opcode
        opcode = self.instructions[self.current_position].opcode.upper()

        # Perform instruction based on the opcode
        if opcode == 'ADD':
            result = (symb1_value + symb2_value, 'int')
        elif opcode == 'SUB':
            result = (symb1_value - symb2_value, 'int')
        elif opcode == 'MUL':
            result = (symb1_value * symb2_value, 'int')
        elif opcode == 'IDIV':
            if symb2_value == 0:
                return 57, "FATAL ERROR: Division by zero"
            result = (symb1_value // symb2_value, 'int')
        else:
            return 32, "Invalid opcode"
        
        # Store the result in the destination variable
        error_code, error_message = self.store_result(var, result)
        return error_code, error_message

    def lt_gt_eq(self, var, symb1, symb2):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Check if the operand types are the same or if one of them is 'nil'
        if symb1_type != symb2_type and (symb1_type != 'nil' and symb2_type != 'nil'):
            return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

        # Get the current opcode
        opcode = self.instructions[self.current_position].opcode.upper()

        # Perform the operation based on the opcode
        if opcode == 'EQ':
            if symb1_type == 'nil' or symb2_type == 'nil':
                result = symb1_type == symb2_type
            else:
                result = symb1_value == symb2_value
        elif opcode in ('LT', 'GT'):
            if symb1_type == 'nil' or symb2_type == 'nil':
                return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

            if opcode == 'LT':
                result = symb1_value < symb2_value
            else:
                result = symb1_value > symb2_value
        else:
            return 32, "Invalid opcode"

        # Store the result in the destination variable
        error_code, error_message = self.store_result(var, (result, 'bool'))
        return error_code, error_message


    def and_or_not(self, var, symb1, symb2=None):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        if (symb1.arg_type != 'bool' and symb1.arg_type != 'var') or (symb2 is not None and symb2.arg_type != 'bool' and symb2.arg_type != 'var'):
            if symb2 is None:
                return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1.arg_type}'"
            else:
                return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1.arg_type}' and '{symb2.arg_type}'"
        
        # Get the value and type of the operand(s)        
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Get the current opcode
        opcode = self.instructions[self.current_position].opcode.upper()

        # Perform instruction based on the opcode
        if opcode == 'AND':
            if symb1_type != 'bool' or symb2_type != 'bool':
                return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

            result = symb1_value and symb2_value

        elif opcode == 'OR':
            if symb1_type != 'bool' or symb2_type != 'bool':
                return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

            result = symb1_value or symb2_value

        elif opcode == 'NOT':
            if symb1_type != 'bool':
                return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: ''"

            result = not symb1_value

        else:
            return 32, f"Invalid opcode {opcode}"

        # Store the result in the destination variable
        result = (result, 'bool')
        error_code, error_message = self.store_result(var, result)
        return error_code, error_message


    def int2char(self, var, symb):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message
        
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)  
        if error_code != 0:
            return error_code, error_message
        
        if symb_type != 'int':
            return 53, f"Unsupported operand type(s): '{symb_type}'"

        # Try to convert the integer to a Unicode character
        try:
            char = chr(symb_value)
        except ValueError:
            return 58, "Invalid Unicode value"

        # Store the result in the destination variable
        error_code, error_message = self.store_result(var, (char, 'string'))
        return error_code, error_message

    def stri2int(self, var, symb1, symb2):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message
        
        # Check if the operand types are 'string' and 'int'
        if symb1_type != 'string' or symb2_type != 'int':
            return 53, f"Unsupported operand type(s): '{symb1_type}' and '{symb2_type}'"

        # Check if the index is within the string bounds
        if symb2_value < 0 or symb2_value >= len(symb1_value):
            return 58, "Invalid string operation: indexing outside the given string"

        # Store the result in the destination variable
        char = symb1_value[symb2_value]
        error_code, error_message = self.store_result(var, (ord(char), 'int'))
        return error_code, error_message

    def read(self, var, type):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message
        
        try:
            # Read from input_lines if available(file input), otherwise read from standard input
            if self.input_line_index < len(self.input_lines):
                input_value = self.input_lines[self.input_line_index]
                self.input_line_index += 1
            else:
                input_value = input()
             
            # Store the input value based on the specified type   
            if type.value.lower() == "string":
                error_code, error_message = self.store_result(var, (input_value, 'string'))
            elif type.value.lower() == "bool":
                error_code, error_message = self.store_result(var, (input_value.lower() == "true", 'bool'))
            elif type.value.lower() == "int":
                intvalue = self.parse_int(input_value)
                if intvalue is None:
                    error_code, error_message = self.store_result(var, ('nil', 'nil'))
                else:
                    error_code, error_message = self.store_result(var, (self.parse_int(input_value), 'int'))
        # Store 'nil' if an error occurs during reading
        except Exception as e:
            error_code, error_message = self.store_result(var, ('nil', 'nil'))
        
        return error_code, error_message

    def write(self, symb):
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)  
        if error_code != 0:
            return error_code, error_message
        
        # Get the current opcode
        opcode = self.instructions[self.current_position-1].opcode.upper()
        
        # Convert the value to a string for output
        if symb_type == 'bool':
            output_value = 'true' if symb_value else 'false'
        elif symb_value is None or (symb_value == 'nil' and symb_type == 'nil'):
            output_value = ''
        else:
            output_value = str(symb_value)

        print(output_value, end='')
        return 0, ""

    def concat(self, var, symb1, symb2):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message
        
        # Check if both operands are strings
        if symb1_type != 'string' or symb2_type != 'string':
            return 53, f"Unsupported operand type(s) '{symb1_type}' or '{symb2_type}'"

        # Store the result in the destination variable
        result = symb1_value + symb2_value
        return self.store_result(var, (result, 'string'))

    def strlen(self, var, symb):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None) 
        if error_code != 0:
            return error_code, error_message
        
        # Check if the operand type is 'string'
        if symb_type != 'string':
            return 53, f"Unsupported operand type(s): '{symb_type}'"

        # Calculate the length of the string and store the result in the destination variable
        string_length = len(symb_value)
        return self.store_result(var, (string_length, 'int'))

    def getchar(self, var, symb1, symb2):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message
        
        # Check if the operand types are 'string' and 'int'
        if symb1_type != 'string' or symb2_type != 'int':
            return 53, f"Unsupported operand type(s): '{symb1_type}' or '{symb2_type}'"

        # Check if the index is within the string indexing
        if symb2_value < 0 or symb2_value >= len(symb1_value):
            return 58, "Invalid string operation: indexing outside the given string"

        # Get the character at the specified index and store the result in the destination variable
        character = symb1_value[symb2_value]
        return self.store_result(var, (character, 'string'))

    def setchar(self, var, symb1, symb2):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (var_value, var_none), (var_type, var_none) = self.get_operand_values(var, None)
        if error_code != 0:
            return error_code, error_message
        if var_type != 'string':
            return 53, "Wrong operand <var> type '{var_type}'"

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message
        
        # Check if the operand types are 'int' and 'string'
        if symb1_type != 'int' or symb2_type != 'string':
            return 53, f"Unsupported operand type(s): '{symb1_type}' or '{symb2_type}'"
        
        # Check if the string operand has a length of at least 1
        if len(symb2_value) == 0:
            return 58, "Invalid string operation: operand <symb2> is of length 0"
        
        # Check if the index is within the string indexing
        if symb1_value < 0 or symb1_value >= len(var_value):
            return 58, "Invalid string operation: indexing outside the given string"

        # Replace the character in the destination string and store the result
        modified_string = var_value[:symb1_value] + symb2_value[0] + var_value[symb1_value + 1:]
        return self.store_result(var, (modified_string, 'string'))


    def type(self, var, symb):
        # Check if the destination variable is defined
        error_code, error_message = self.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        symb_value, symb_type = None, None
        if symb.arg_type == 'var':
            # Get the value and type of the operand(s)
            error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
            if error_code == 56:  # Uninitialized variable
                symb_type = ''
            elif error_code != 0:
                return error_code, error_message
        else:
            # Set the type directly if the operand is not a variable
            symb_type = symb.arg_type

        # Store the result in the destination variable
        return self.store_result(var, (symb_type, 'string'))

    def label(self, label):
        # Labels are already pre-processed by XMLParser
        return 0, ""

    def jump(self, label):
        if label.value not in self.labels:
            return 52, f"Undefined label {label.value}"

        label_order = self.labels[label.value]
        
        for i, instruction in enumerate(self.instructions):
            if instruction.order == label_order:
                self.current_position = i
                break

        return 0, ""

    def jumpif(self, label, symb1, symb2):
        if label.value not in self.labels:
            return 52, f"Undefined label {label.value}"
        
        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = self.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message
        
        # Get the current opcode
        opcode = self.instructions[self.current_position].opcode.upper()
        
        # Compare the operands if their types match or if either is 'nil'
        if symb1_type == symb2_type or symb1_type == 'nil' or symb2_type == 'nil':
            if opcode == 'JUMPIFEQ':
                if symb1_value == symb2_value:
                    return self.jump(label)
                else:
                    return 0, ""
            elif opcode == 'JUMPIFNEQ':
                if symb1_value != symb2_value:
                    return self.jump(label)
                else:
                    return 0, ""   
            else:
                return 32, f"Invalid opcode {opcode}"   
        
        return 53, f"Unsupported operand type(s) for {self.instructions[self.current_position].opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

    def exit(self, symb):
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = self.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message
        
        # Check if the operand type is 'int'
        if symb_type != 'int':
            return 53, f"Unsupported operand type(s) '{symb_type}'"
        
        # Check if the exit code is within the valid range (0-49), and exit the program with exit code
        if 0 <= symb_value <= 49:
            sys.exit(symb_value)
        return 57, f"Invalid exit code {symb_value}"
    
    # Prints value of symbol to debug(stderr)
    def dprint(self, symb):
        print(symb.value, file=sys.stderr)
        return 0, ""

    # Prints information about program that is being interpreted
    def break_instruction(self):
        # TODO!!! prints objects instead of values in Frames
        print(f"Position in code: {self.current_position+1}", file=sys.stderr)
        print(f"Global frame: {self.frames['GF']}", file=sys.stderr)
        print(f"Local frame: {self.frames['LF']}", file=sys.stderr)
        print(f"Temporary frame: {self.frames['TF']}", file=sys.stderr)
        print(f"Number of successfully executed instructions: {self.executed_instructions_count}", file=sys.stderr)
        return 0, ""
    
    def execute_instructions(self):
        instr_name=""
        while self.current_position < len(self.instructions):
            instruction = self.instructions[self.current_position]

            instr_name = instruction.opcode.upper()
            instr_name = instr_name.strip()
            args = instruction.args

            try:
                # instruction mapping
                if instr_name in self.instruction_mapping:
                    method = self.instruction_mapping[instr_name]
                    # Unpack the args to method
                    error_code, error_message = method(*args)
                else:
                    raise KeyError(f"Invalid instruction name: {instr_name}")

                if error_code != 0:
                    return error_code, error_message, self.current_position, instr_name

                self.executed_instructions_count += 1
                self.current_position += 1
            except Exception as e:
                return -1, str(e)
            if 0 < error_code < 49:
                break
        return 0, "", self.current_position, instr_name

# parse command-line arguments
args = argparser()

# open source file
if args.source:
    try:
        with open(args.source, "r") as file:
            xml_string = file.read()
    except IOError:
        print(f"Error: Could not read file '{args.source}'", file=sys.stderr)
        sys.exit(11)
else:
    xml_string = sys.stdin.read()
    
# open input file
if args.input:
    try:
        with open(args.input, "r") as file:
            input_lines = [line.rstrip() for line in file]
    except IOError:
        print(f"Error: Could not read input file '{args.input}'", file=sys.stderr)
        sys.exit(11)
else:
    input_lines = []
    
# read XML input, parse it and store to xmlparser
xmlparser = XMLParser(xml_string)
error_code, error_message = xmlparser.validate()
if error_code:
    print(f"ERROR {error_code}: {error_message}", file=sys.stderr)
    exit(error_code)

# load instructions from xmlparser
instructions, labels, error_code, error_message = xmlparser.validate_instructions()  
if error_code:
    print(f"ERROR {error_code}: {error_message}", file=sys.stderr)
    exit(error_code)

# create instance of interpreter class with, store input, execute instructions
interpreter = IPPInterpreter(instructions, labels, input_lines)
error_code, error_message, current_position, instr_name = interpreter.execute_instructions()

if error_code != 0:
    print(f"ERROR {error_code} at instr. order {current_position+1} '{instr_name}': {error_message}", file=sys.stderr)

sys.exit(error_code)

