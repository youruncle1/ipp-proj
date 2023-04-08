<?php
/*
IPP 22/23 Projekt 1 - skript parse.php
autor: xpolia05
*/

ini_set('display_errors', 'stderr');

function parsearguments(){
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
        exit(0);
    }
}#parsearguments()

#kontrola hlavicky .IPPcode23
function headercheck($file){
    while(true){
        $line = fgets($file);
        $header = explode("#", $line); 
        $header = trim($header[0]);
        if (empty($header)) #preskoci prazdne/komentovane riadky pred hlavickou
            continue;
        break;
    }
    
    if (strtoupper($header) != ".IPPCODE23"){
        fwrite(STDERR, "Error: incorrect or missing header in trhe source code written in IPPcode23." . PHP_EOL);
        exit(21);
    }
}#headercheck()

#upravi nacitany riadok tak, aby sa mohol predat analyzatoru
function contentcut(&$line){
    $line = preg_replace('!\s+!', ' ', $line); #zamena duplikatov whitespaces za singularny
    $line = trim($line);
    $line = explode('#', $line);
    $line = $line[0];
    $line = trim($line); #potrebny trim, ak bol komentar oddeleny medzerou od zdrojoveho kodu
}#contentcut()

#lex. kontrola neterminalu <var>
function isvar($token){
    if (preg_match( "/^(LF|TF|GF)@[a-zA-Z_\-$&%*!?][a-zA-Z0-9_\-$&%*!?]*$/", $token))
        return true;
    else
        return false;
}#isvar()

#lex. kontrola neterminalu <type>
function istype($token){
    if (preg_match("/^(bool|int|string)$/", $token))
        return true;
    else
        return false;
}#istype()

#lex. kontrola neterminalu <symb>
function issymb($token){
    if (isvar($token)){
        return "var";
    }
    elseif (preg_match("/^int@(?:\+|-)?(?:(?!.*_{2})(?!0\d)\d+(?:_\d+)*|0[oO]?[0-7]+(_[0-7]+)*|0[xX][0-9a-fA-F]+(_[0-9a-fA-F]+)*)$/", $token)){
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
}#issymb()

#lex. kontrola neterminalu <label>
function islabel($token){
    if (preg_match("/^[a-zA-Z\-_$&%*!?][a-zA-Z0-9\-_$&%*!?]*$/", $token))
        return true;
    else
        return false;
}#islabel()

#XML zapis pre <var>|<label>
function XMLaddVarLabel(&$XML, &$instruction, &$instructcnt, $token, $type){
    $instruction = $XML->addChild('instruction');
    $instruction->addAttribute('order', $instructcnt);
    $instruction->addAttribute('opcode', $token[0]);
    $arg1 = $instruction->addChild('arg1', htmlspecialchars($token[1], ENT_XML1, 'UTF-8'));
    $arg1->addAttribute('type', $type);
    $instructcnt++;
}#XMLaddVarLabel()

#XML zapis pre <symb>
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
}#XMLaddSymb()


#hlavna funkcia analyzatoru
function parse($file){
    
    headercheck($file);

    $XML = new SimpleXMLElement('<?xml version="1.0" encoding="UTF-8"?><program></program>');
    $XML->addAttribute('language', 'IPPcode23');
    $instruction; #uklada aktualne nacitanu instrukciu
    $instructcnt = 1; #counter instrukcii
    
    while ($line = fgets(STDIN)){
        
        contentcut($line);
        
        if(empty($line))
            continue;

        $token = explode(' ', $line);
        $token[0] = strtoupper($token[0]); #token[0] == instrukcia
        
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
}#parse()

parsearguments();
parse(STDIN);

?>