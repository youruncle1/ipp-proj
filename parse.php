<?php
/*
IPP 22/23 Projekt 1 - skript parse.php
autor: xpolia05
*/

ini_set('display_errors', 'stderr');

function parsecmdline(){
    $options = getopt(null, ['help', 'stats', 'loc', 'comments', 'labels', 'jumps', 'fwjumps', 'backjumps', 'badjumps', 'frequent', 'print', 'eol']);

    if (isset($options['help'])) {
        if (count($options) > 1) {
            fwrite(STDERR, "Error: --help cannot be combined with other options." . PHP_EOL);
            exit(10);
        }
        echo "\t####  IPPcode23 code analyzer ####\n";
        echo "\tScript of filter type reads the source code in IPPcode23 from STDIN,\n\tchecks code for lexcal and syntactic correctness and\n\tprints it in standard XML representation to the STDOUT.\n\n";
        echo "Usage: php8.1 parse.php [OPTIONS]\n";
        echo "Options:\n";
        echo "  --help          Display this help message and exit.\n";
        /*echo "  --stats=file    Specify a file to write statistics to.\n";
        echo "  --loc           Count lines of code.\n";
        echo "  --comments      Count lines with comments.\n";
        echo "  --labels        Count unique labels.\n";
        echo "  --jumps         Count jump instructions.\n";
        echo "  --fwjumps       Count forward jump instructions.\n";
        echo "  --backjumps     Count backward jump instructions.\n";
        echo "  --badjumps      Count bad jump instructions(jumps to undef. label).\n";
        echo "  --frequent      Find most frequently used instructions.\n";
        echo "  --print         Print out a string into statistics file.\n";
        echo "  --eol           Print out an end-of-line into statistics file.\n";
        */
        exit(0);
    }
}


function headercheck($file){
    while(true){
        $line = fgets($file);
        $header = explode("#", $line);
        $header = trim($header[0]);
        if (empty($header))
            continue;
        break;
    }
    
    if (strtoupper($header) != ".IPPCODE23"){
        fwrite(STDERR, "Error: incorrect or missing header in trhe source code written in IPPcode23." . PHP_EOL);
        exit(21);
    }

}

function contentcut(&$line){
    $line = preg_replace('!\s+!', ' ', $line);
    $line = trim($line);
    $line = explode('#', $line);
    $line = $line[0];
    $line = trim($line);
}

function isvar($token){
    if (preg_match( "/^(LF|TF|GF)@[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$/", $token))
        return true;
    else
        return false;
}

function istype($token){
    if (preg_match("/^(bool|int|string)$/", $token))
        return true;
    else
        return false;
}

function issymb($token){
    if (isvar($token)){
        return "var";
    }
    elseif (preg_match("/^int@[-+]?\d+$/", $token)){
        return "int";
    }
    elseif (preg_match("/^nil@nil$/", $token)){
        return "nil";
    }
    elseif (preg_match("/^bool@(true|false)$/", $token)){
        return "bool";
    }
    elseif (preg_match("/^string@([^\\\\]|\\\\\d{3})*$/", $token)){
        return "string"; 
    }
    else{
        return false;
    }
}

function islabel($token){
    if (preg_match("/^[a-zA-Z\-_$&%*!?][a-zA-Z0-9\-_$&%*!?]*$/", $token))
        return true;
    else
        return false;
}

function XMLaddVarLabel(&$XML, &$instruction, &$instructcnt, $token, $type){
    $instruction = $XML->addChild('instruction');
    $instruction->addAttribute('order', $instructcnt);
    $instruction->addAttribute('opcode', $token[0]);
    $arg1 = $instruction->addChild('arg1', htmlspecialchars($token[1], ENT_XML1, 'UTF-8'));
    $arg1->addAttribute('type', $type);
    $instructcnt++;
}

function XMLaddSymb(&$XML, &$instruction, $token, $symb, $argn){
    switch($symb){
        case 'var':
            $arg2 = $instruction->addChild('arg'.$argn, htmlspecialchars($token[$argn], ENT_XML1, 'UTF-8'));
            $arg2->addAttribute('type', $symb);
            break;
        case 'int':
        case 'nil':
        case 'bool':
        case 'string':
            $symbval = explode('@', $token[$argn]);
            $symbval = $symbval[1];
            $arg2 = $instruction->addChild('arg'.$argn, htmlspecialchars($symbval, ENT_XML1, 'UTF-8'));
            $arg2->addAttribute('type', $symb);
            break;
    }
}

function parse($file){
    
    headercheck($file);

    $XML = new SimpleXMLElement('<?xml version="1.0" encoding="UTF-8"?><program></program>');
    $XML->addAttribute('language', 'IPPcode23');
    $instruction;
    $instructcnt = 1;
    
    while ($line = fgets(STDIN)){
        
        contentcut($line);
        
        if(empty($line))
            continue;

        $token = explode(' ', $line);
        $token[0] = strtoupper($token[0]);
        switch($token[0]){
            #### <> ####
            case 'CREATEFRAME':
            case 'PUSHFRAME':
            case 'POPFRAME':
            case 'RETURN':
            case 'BREAK':
                if(sizeof($token) != 1){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                $instruction = $XML->addChild('instruction');
                $instruction->addAttribute('order',$instructcnt);
                $instruction->addAttribute('opcode',$token[0]);
                $instructcnt++;
                break;
            
            #### <VAR> ####
            case 'DEFVAR':
            case 'POPS':
                if((sizeof($token) != 2) or (!isvar($token[1]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                
                XMLaddVarLabel($XML, $instruction, $instructcnt, $token, "var");
                break;
            
            #### <VAR> <TYPE> ####
            case 'READ':
                if((sizeof($token) != 3) or (!isvar($token[1])) or (!istype($token[2]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                
                XMLaddVarLabel($XML, $instruction, $instructcnt, $token, "var");
                $arg2 = $instruction->addChild('arg2', htmlspecialchars($token[2], ENT_XML1, 'UTF-8'));
                $arg2->addAttribute('type', 'type');
                break;

            #### <VAR> <SYMB> ####
            case 'MOVE':
            case 'INT2CHAR':
            case 'STRLEN':
            case 'NOT':
            case 'TYPE':
                if(sizeof($token) != 3 or !(isvar($token[1])) or !($symb = issymb($token[2]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }

                XMLaddVarLabel($XML, $instruction, $instructcnt, $token, "var");
                XMLaddSymb($XML, $instruction, $token, $symb, 2);
                break;
            
            #### <VAR> <SYMB1> <SYMB2> ####
            case 'ADD':
            case 'SUB':
            case 'MUL':
            case 'IDIV':
            case 'LT':
            case 'GT':
            case 'EQ':                           
            case 'AND':
            case 'OR':
            case 'STRI2INT':
            case 'CONCAT':
            case 'GETCHAR':
            case 'SETCHAR':
                if(sizeof($token) != 4 or !isvar($token[1]) or !($symb1 = issymb($token[2])) or !($symb2 = issymb($token[3]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                
                XMLaddVarLabel($XML, $instruction, $instructcnt, $token, "var");
                XMLaddSymb($XML, $instruction, $token, $symb1, 2);
                XMLaddSymb($XML, $instruction, $token, $symb2, 3);
                break;

            #### <SYMB> ####
            case 'PUSHS':
            case 'WRITE':
            case 'EXIT':
            case 'DPRINT':
                if(sizeof($token) != 2 or !($symb = issymb($token[1]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                
                $instruction = $XML->addChild('instruction');
                $instruction->addAttribute('order', $instructcnt);
                $instruction->addAttribute('opcode', $token[0]);
                $instructcnt++;
                XMLaddSymb($XML, $instruction, $token, $symb, 1);
                break;
            
            #### <LABEL> ####
            case 'CALL':
            case 'LABEL':
            case 'JUMP':
                if((sizeof($token) != 2) or (!islabel($token[1]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                
                XMLaddVarLabel($XML, $instruction, $instructcnt, $token, "label");
                break;
            
            #### <LABEL> <SYMB1> <SYMB2> ####
            case 'JUMPIFEQ':
            case 'JUMPIFNEQ':
                if(sizeof($token) != 4 or !islabel($token[1]) or !($symb1 = issymb($token[2])) or !($symb2 = issymb($token[3]))){
                    fwrite(STDERR, "Error: lexical or syntax error in the source code written in IPPcode23" . PHP_EOL);
                    exit(23);
                }
                
                XMLaddVarLabel($XML, $instruction, $instructcnt, $token, "label");
                XMLaddSymb($XML, $instruction, $token, $symb1, 2);
                XMLaddSymb($XML, $instruction, $token, $symb2, 3);
                break;
            
            default:
                fwrite(STDERR, "Error: unknown or incorrect OPCODE in the source code written in IPPcode23" . PHP_EOL);
                exit(22);
        }#switch
    }#while
    echo $XML->asXML();
}#func

parsecmdline();
$file = STDIN;
parse($file);


?>