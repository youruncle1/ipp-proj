'''
IPP 22/23 Projekt 2 -  Interpret XML reprezentace kódu (interpret.py)
autor: xpolia05
'''

import argparse
import sys
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod

# Parses command-line arguments
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

# Replaces unicode escape sequences to ascii (e.g. \035 -> #)
def replace_escapeSequences(match):
    return chr(int(match.group(0)[1:]))

## Abstract class Instruction stores instruction's order, OPCODE and it's arguments as objects of class Argument
class Instruction(ABC):
    def __init__(self, order, opcode, args):
        self.order = order
        self.opcode = opcode
        self.args = sorted(args, key=lambda x: x.order)

    @abstractmethod
    def execute(self, interpreter):
        pass

## class Argument stores argument's datatype, value and it's order in instruction
class Argument:
    def __init__(self, arg_type, value, order):
        self.arg_type = arg_type
        self.value = value
        self.order = order 

## class XMLParser validates an IPPcode23 program formatted in XML
class XMLParser:
    def __init__(self, xml_string):
        # Parse the xml_string using xml.etree.ElementTree and store to root attribute
        try:
            self.root = ET.fromstring(xml_string)
        except ET.ParseError:
            self.root = None
    
    # valid opcodes : required number of arguments 
    @property
    def valid_opcodes(self):
        return {
            'CREATEFRAME': 0, 'PUSHFRAME': 0, 'POPFRAME': 0, 'RETURN': 0, 'BREAK': 0,
            'DEFVAR': 1, 'POPS': 1, 'CALL': 1, 'LABEL': 1, 'JUMP': 1, 'PUSHS': 1, 'WRITE': 1, 'EXIT': 1, 'DPRINT': 1,
            'MOVE': 2, 'INT2CHAR': 2, 'NOT': 2, 'STRLEN': 2, 'TYPE': 2, 'READ': 2,
            'ADD': 3, 'SUB': 3, 'MUL': 3, 'IDIV': 3, 'LT': 3, 'GT': 3, 'EQ': 3, 'AND': 3, 'OR': 3, 'STRI2INT': 3, 'CONCAT': 3, 'GETCHAR': 3, 'SETCHAR': 3, 'JUMPIFEQ': 3, 'JUMPIFNEQ': 3
        }

    # regex patterns for validating argument types
    @property
    def valid_argtypes(self):
        return {
            "var": r"^(LF|TF|GF)@[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$",
            "type": r"^(bool|int|string)$",
            "label": r"^[a-zA-Z\-_$&%*!?][a-zA-Z0-9\-_$&%*!?]*$",
            "nil": r"^nil$",
            "string": r"^([^\\]|\\\d{3})*$",
            "bool": r"^(true|false)$",
            "int": r"^(?:\+|-)?(?:(?!.*_{2})(?!0\d)\d+(?:_\d+)*|0[oO]?[0-7]+(_[0-7]+)*|0[xX][0-9a-fA-F]+(_[0-9a-fA-F]+)*)$"
        }

    # map opcodes to subclasses of abstract class Instructiom
    @property
    def opcode_to_class_map(self):
        return {
            'MOVE': Move,
            'CREATEFRAME': CreateFrame,
            'PUSHFRAME': PushFrame,
            'POPFRAME': PopFrame,
            'DEFVAR': DefVar,
            'CALL': Call,
            'RETURN': ReturnInstruction,
            'PUSHS': Pushs,
            'POPS': Pops,
            'ADD': AddSubMulIdiv,
            'SUB': AddSubMulIdiv,
            'MUL': AddSubMulIdiv,
            'IDIV': AddSubMulIdiv,
            'LT': LtGtEq,
            'GT': LtGtEq,
            'EQ': LtGtEq,
            'AND': AndOrNot,
            'OR': AndOrNot,
            'NOT': AndOrNot,
            'INT2CHAR': Int2Char,
            'STRI2INT': Stri2Int,
            'READ': Read,
            'WRITE': Write,
            'CONCAT': Concat,
            'STRLEN': Strlen,
            'GETCHAR': Getchar,
            'SETCHAR': Setchar,
            'TYPE': Type,
            'LABEL': Label,
            'JUMP': Jump,
            'JUMPIFEQ': Jumpif,
            'JUMPIFNEQ': Jumpif,
            'EXIT': Exit,
            'DPRINT': Dprint,
            'BREAK': Break
        }
        
    @staticmethod
    def remove_whitespace_from_xml(xml_string):

        try:
            tree = ET.ElementTree(ET.fromstring(xml_string))
            root = tree.getroot()
        except ET.ParseError:
            return "", 31, "XML parse error"
        # Remove whitespace from elements
        def remove_whitespace(element):
            if element.text:
                element.text = element.text.strip()
            if element.tail:
                element.tail = element.tail.strip()
            for child in element:
                remove_whitespace(child)

        remove_whitespace(root)

        # Convert the new XML back to a string
        return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8'), 0, ""

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

        opcode_class = self.opcode_to_class_map.get(opcode.upper())
        if opcode_class is None:
            return None, 32, f"Invalid opcode name '{opcode}' in Instruction Order {order}"
        
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

        return opcode_class(order, opcode, args), 0, None

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
#### END OF CLASS XMLParser

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
        if input_lines is None or len(input_lines) == 0:
            self.input_lines = []
            self.has_input = False
        else:
            self.input_lines = input_lines
            self.has_input = True
        self.input_line_index = 0

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
        
    def execute_instructions(self):
        instr_name = ""
        
        while self.current_position < len(self.instructions):
            instruction = self.instructions[self.current_position]
            instr_name = instruction.opcode.upper()
            instr_name = instr_name.strip()
            args = instruction.args

            try:
                error_code, error_message = instruction.execute(self)

                if error_code != 0:
                    return error_code, error_message, self.current_position, instr_name

                self.executed_instructions_count += 1
                self.current_position += 1
            except Exception as e:
                return -1, str(e), self.current_position, instr_name

        return 0, None, self.current_position, instr_name
#### END OF CLASS IPPInterpreter 


class Move(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)
        
    def execute(self, interpreter):
        self.var, self.symb = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(self.var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(self.symb, None)
        if error_code != 0:
            return error_code, error_message
        
        # Store the result in the destination variable
        error_code, error_message = interpreter.store_result(self.var, (symb_value, symb_type))
        return error_code, error_message

class CreateFrame(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        # Create a new temporary frame (TF)
        interpreter.frames['TF'] = {}
        return 0, ""

class PushFrame(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        # Check if the temporary frame (TF) is defined
        if interpreter.frames['TF'] is None:
            return 55, "Push to undefined frame (TF)"

        # Push the temporary frame (TF) onto the frame stack and set it as the local frame (LF)
        interpreter.frame_stack.append(interpreter.frames['TF'])
        interpreter.frames['LF'] = interpreter.frames['TF']
        interpreter.frames['TF'] = None
        return 0, ""

class PopFrame(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        if interpreter.frames['LF'] is None:
            return 55, "Pop from undefined frame (LF)"

        interpreter.frames['TF'] = interpreter.frames['LF']
        interpreter.frame_stack.pop()
        if len(interpreter.frame_stack) > 0:
            interpreter.frames['LF'] = interpreter.frame_stack[-1]
        else:
            interpreter.frames['LF'] = None

        return 0, ""
    
class DefVar(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        variable = self.args[0].value

        # Check if the frame exists
        frame_name, var_name = variable.split('@')
        if frame_name not in interpreter.frames or interpreter.frames[frame_name] is None:
            return 55, f"Accessing '{var_name}' in Frame '{frame_name}', '{frame_name}' does not exist"

        # Check if the variable is already defined in the frame
        if var_name in interpreter.frames[frame_name]:
            return 52, f"Redefining existing variable {var_name} in Frame {frame_name}"

        # Define the variable in the frame
        interpreter.frames[frame_name][var_name] = None
        return 0, ""

class Call(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        label = self.args[0].value

        # Check if the label exists
        if label not in interpreter.labels:
            return 52, f"Call to Undefined label '{label}'"
        
        # Save the current position on the call stack and jump to the label
        interpreter.call_stack.append(interpreter.current_position)
        # use new instance of instruction Jump and execute it
        jump_instruction = Jump(self.order, "JUMP", [self.args[0]])
        return jump_instruction.execute(interpreter)

class ReturnInstruction(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        # Check if the call stack is empty
        if len(interpreter.call_stack) == 0:
            return 56, "Return: Empty call stack"

         # Pop the saved position from the call stack and set the current position
        interpreter.current_position = interpreter.call_stack.pop()
        return 0, ""

class Pushs(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(self.args[0], None)
        if error_code != 0:
            return error_code, error_message

        # Push the value and type onto the data stack
        interpreter.data_stack.append((symb_value, symb_type))
        return 0, ""

class Pops(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(self.args[0].value)
        if error_code:
            return error_code, error_message

        # Check if the data stack is empty
        if len(interpreter.data_stack) == 0:
            return 56, "Pops: Empty data stack"

        # Pop the value and type from the data stack
        symb_value, symb_type = interpreter.data_stack.pop()

        # Store the result in the destination variable
        error_code, error_message = interpreter.store_result(self.args[0], (symb_value, symb_type))
        return error_code, error_message
    
class AddSubMulIdiv(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message
        
        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Check if both operands are integers
        if symb1_type != 'int' or symb2_type != 'int':
            return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

        # Get the current opcode
        opcode = self.opcode.upper()

        # Use instruction based on the opcode
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
        error_code, error_message = interpreter.store_result(var, result)
        return error_code, error_message

class LtGtEq(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Check if the operand types are the same or if one of them is 'nil'
        if symb1_type != symb2_type and (symb1_type != 'nil' and symb2_type != 'nil'):
            return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

        # Get the current opcode
        opcode = self.opcode.upper()

        # Use instruction based on the opcode
        if opcode == 'EQ':
            if symb1_type == 'nil' or symb2_type == 'nil':
                result = symb1_type == symb2_type
            else:
                result = symb1_value == symb2_value
        elif opcode in ('LT', 'GT'):
            if symb1_type == 'nil' or symb2_type == 'nil':
                return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

            if opcode == 'LT':
                result = symb1_value < symb2_value
            else:
                result = symb1_value > symb2_value
        else:
            return 32, "Invalid opcode"

        # Store the result in the destination variable
        error_code, error_message = interpreter.store_result(var, (result, 'bool'))
        return error_code, error_message

class AndOrNot(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        opcode = self.opcode.upper()

        if opcode == 'NOT':
            var, symb1 = self.args
            symb2 = None
        else:
            var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined  
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        if (symb1.arg_type != 'bool' and symb1.arg_type != 'var') or (symb2 is not None and symb2.arg_type != 'bool' and symb2.arg_type != 'var'):
            if symb2 is None:
                return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1.arg_type}'"
            else:
                return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1.arg_type}' and '{symb2.arg_type}'"

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Use instruction based on the opcode
        if opcode == 'AND':
            if symb1_type != 'bool' or symb2_type != 'bool':
                return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

            result = symb1_value and symb2_value

        elif opcode == 'OR':
            if symb1_type != 'bool' or symb2_type != 'bool':
                return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: '{symb1_type}' and '{symb2_type}'"

            result = symb1_value or symb2_value

        elif opcode == 'NOT':
            if symb1_type != 'bool':
                return 53, f"Unsupported operand type(s) for {self.opcode.upper()}: ''"

            result = not symb1_value

        else:
            return 32, f"Invalid opcode {opcode}"

        # Store the result in the destination variable
        result = (result, 'bool')
        error_code, error_message = interpreter.store_result(var, result)
        return error_code, error_message


class Int2Char(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message

        if symb_type != 'int':
            return 53, f"Unsupported operand type(s): '{symb_type}'"

        # Try to convert the integer to a Unicode character using chr()
        try:
            char = chr(symb_value)
        except ValueError:
            return 58, "Invalid Unicode value"

        # Store the result in the destination variable
        error_code, error_message = interpreter.store_result(var, (char, 'string'))
        return error_code, error_message

class Stri2Int(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
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
        error_code, error_message = interpreter.store_result(var, (ord(char), 'int'))
        return error_code, error_message


class Read(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, type = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        try:
            # Read from input_lines if available(file input), otherwise read from standard input
            if interpreter.input_line_index < len(interpreter.input_lines) or not interpreter.has_input:
                input_value = interpreter.input_lines[interpreter.input_line_index] if interpreter.has_input else ''
                interpreter.input_line_index += 1
            else:
                input_value = input()

            # Store the input value based on the specified type 
            if type.value.lower() == "string":
                error_code, error_message = interpreter.store_result(var, (input_value, 'string'))
            elif type.value.lower() == "bool":
                error_code, error_message = interpreter.store_result(var, (input_value.lower() == "true", 'bool'))
            elif type.value.lower() == "int":
                intvalue = interpreter.parse_int(input_value)
                if intvalue is None:
                    error_code, error_message = interpreter.store_result(var, ('nil', 'nil'))
                else:
                    error_code, error_message = interpreter.store_result(var, (interpreter.parse_int(input_value), 'int'))
        # Store 'nil' if an error happens during reading
        except Exception as e:
            error_code, error_message = interpreter.store_result(var, ('nil', 'nil'))

        return error_code, error_message


class Write(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        symb = self.args[0]
        
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message

        # Get the current opcode
        opcode = self.opcode.upper()

        # Convert the value to a string for output
        if symb_type == 'bool':
            output_value = 'true' if symb_value else 'false'
        elif symb_value is None or (symb_value == 'nil' and symb_type == 'nil'):
            output_value = ''
        else:
            output_value = str(symb_value)

        print(output_value, end='')
        return 0, ""

class Concat(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message

        # Check if both operands are strings
        if symb1_type != 'string' or symb2_type != 'string':
            return 53, f"Unsupported operand type(s) '{symb1_type}' or '{symb2_type}'"

        # Store the result in the destination variable
        result = symb1_value + symb2_value
        return interpreter.store_result(var, (result, 'string'))


class Strlen(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message

        # Check if the operand type is 'string'
        if symb_type != 'string':
            return 53, f"Unsupported operand type(s): '{symb_type}'"

        # Getthe length of the string and store the result in the destination variable
        string_length = len(symb_value)
        return interpreter.store_result(var, (string_length, 'int'))

class Getchar(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
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
        return interpreter.store_result(var, (character, 'string'))


class Setchar(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb1, symb2 = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        # Get the value and type of the operand(s)
        error_code, error_message, (var_value, var_none), (var_type, var_none) = interpreter.get_operand_values(var, None)
        if error_code != 0:
            return error_code, error_message
        if var_type != 'string':
            return 53, "Wrong operand <var> type '{var_type}'"

        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
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
        return interpreter.store_result(var, (modified_string, 'string'))


class Type(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        var, symb = self.args
        
        # Check if the destination variable is defined
        error_code, error_message = interpreter.is_variable_defined(var.value)
        if error_code:
            return error_code, error_message

        symb_value, symb_type = None, None
        if symb.arg_type == 'var':
            # Get the value and type of the operand(s)
            error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(symb, None)
            if error_code == 56:  # Uninitialized variable
                symb_type = ''
            elif error_code != 0:
                return error_code, error_message
        else:
            # Set the type directly if the operand is not a variable
            symb_type = symb.arg_type

        return interpreter.store_result(var, (symb_type, 'string'))


class Label(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        # Labels are already pre-processed by XMLParser
        return 0, ""


class Jump(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        label = self.args[0]
        
        # Check if label is defined
        if label.value not in interpreter.labels:
            return 52, f"Undefined label {label.value}"

        label_order = interpreter.labels[label.value]
        
        for i, instruction in enumerate(interpreter.instructions):
            if instruction.order == label_order:
                interpreter.current_position = i
                break

        return 0, ""

class Jumpif(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        label, symb1, symb2 = self.args
        
        # Check if label is defined
        if label.value not in interpreter.labels:
            return 52, f"Undefined label {label.value}"
        
        # Get the value and type of the operand(s)
        error_code, error_message, (symb1_value, symb2_value), (symb1_type, symb2_type) = interpreter.get_operand_values(symb1, symb2)
        if error_code != 0:
            return error_code, error_message
        
        # Get the current opcode
        opcode = self.opcode.upper()
        
        # Compare the operands if their types match or if either is 'nil'
        if symb1_type == symb2_type or symb1_type == 'nil' or symb2_type == 'nil':
            jump_instruction = Jump(self.order, "JUMP", [label])  # Create a new Jump instance with the same order and label
            if opcode == 'JUMPIFEQ':
                if symb1_value == symb2_value:
                    return jump_instruction.execute(interpreter)
                else:
                    return 0, ""
            elif opcode == 'JUMPIFNEQ':
                if symb1_value != symb2_value:
                    return jump_instruction.execute(interpreter)
                else:
                    return 0, ""   
            else:
                return 32, f"Invalid opcode {opcode}"   
        
        return 53, f"Unsupported operand type(s) for {opcode}: '{symb1_type}' and '{symb2_type}'"

class Exit(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        symb = self.args[0]
        
        # Get the value and type of the operand(s)
        error_code, error_message, (symb_value, symb_none), (symb_type, symb_none) = interpreter.get_operand_values(symb, None)
        if error_code != 0:
            return error_code, error_message
        
        # Check if the operand type is 'int'
        if symb_type != 'int':
            return 53, f"Unsupported operand type(s) '{symb_type}'"
        
        # Check if the exit code is within the valid range (0-49), and exit the program with exit code
        if 0 <= symb_value <= 49:
            sys.exit(symb_value)
        return 57, f"Invalid exit code {symb_value}"


class Dprint(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        symb = self.args[0]
        print(symb.value, file=sys.stderr)
        return 0, ""


class Break(Instruction):
    def __init__(self, order, opcode, args):
        super().__init__(order, opcode, args)

    def execute(self, interpreter):
        print(f"Position in code: {interpreter.current_position+1}", file=sys.stderr)
        print(f"Global frame: {interpreter.frames['GF']}", file=sys.stderr)
        print(f"Local frame: {interpreter.frames['LF']}", file=sys.stderr)
        print(f"Temporary frame: {interpreter.frames['TF']}", file=sys.stderr)
        print(f"Number of successfully executed instructions: {interpreter.executed_instructions_count}", file=sys.stderr)
        return 0, ""



# Parse command-line arguments
args = argparser()

# Open source file or read fro stdin
if args.source:
    try:
        with open(args.source, "r") as file:
            xml_string = file.read()
    except IOError:
        print(f"Error: Could not read file '{args.source}'", file=sys.stderr)
        sys.exit(11)
else:
    xml_string = sys.stdin.read()
    
# Open input file or read from stdin
if args.input:
    try:
        with open(args.input, "r") as file:
            input_lines = [line.rstrip() for line in file]
    except IOError:
        print(f"Error: Could not read input file '{args.input}'", file=sys.stderr)
        sys.exit(11)
else:
    input_lines = []

# Remove whitespaces from the elements in XML string
xml_string, error_code, error_message = XMLParser.remove_whitespace_from_xml(xml_string)
if error_code:
    print(f"ERROR {error_code}: {error_message}", file=sys.stderr)
    exit(error_code)
    
# Read XML input, parse it and store to xmlparser
xmlparser = XMLParser(xml_string)
error_code, error_message = xmlparser.validate()
if error_code:
    print(f"ERROR {error_code}: {error_message}", file=sys.stderr)
    exit(error_code)

# Load instructions and labels from xmlparser
instructions, labels, error_code, error_message = xmlparser.validate_instructions()  
if error_code:
    print(f"ERROR {error_code}: {error_message}", file=sys.stderr)
    exit(error_code)

# Create instance of interpreter class, store instructions and labels from XMLParser, input, and execute instructions
interpreter = IPPInterpreter(instructions, labels, input_lines)
error_code, error_message, current_position, instr_name = interpreter.execute_instructions()

if error_code != 0:
    print(f"ERROR {error_code} at instr. order {current_position+1} '{instr_name}': {error_message}", file=sys.stderr)

sys.exit(error_code)