# Implementačná dokumentácia k 1. úlohe IPP 22/23
jméno a příjmení: Roman Poliačik
login: __xpolia05__

### 1. Úvod

Úlohou bolo implementovať skript typu filter parse.php v jazyku PHP8.1, ktorý číta zdrojový kód v IPPcode23 zo STDIN, skontroluje kód z hľadiska lexikálnej a syntaktickej správnosti a vypíše ho v štandardnej reprezentácii XML na STDOUT.

### 2. Implementácia

Základom riešenia je použitie vstavanej triedy `SimpleXMLElement`, ktorá zabezpečuje zostavenie a generovanie kódu XML.
Hlavnou funkciou skriptu je funkcia `parse()`, v ktorej sa prv skontroluje správnosť hlavičky funkciou `headercheck()` a vytvorí nový objekt `XML` triedy `SimpleXMLElement`. Syntaktická kontrola prebieha formou konečného automatu implementovaného pomocou cyklu a prepínača. Každou iteráciou sa pomocou `fgets()` načíta jeden riadok zo vstupu, vymažú sa z neho prebytočné whitespaces a komentáre funkciou `contentcut()`. 
V následujúcom prepínači sú inštrukcie jazyka IPPcode23 rozdelené do skupín podľa počtu a druhov operandov. Na základe typu načítanej inštrukcie sa overí správny počet operandov a ich správnosť funkciami `isvar()`, `issymb()`, `islabel()` alebo `istype()` využívajúc porovnania regulárnych výrazov(regex matching). Pre regexovú kontrolu čísiel som použil na hexadecimálne a oktálové čísla regexový zápis z oficiálnej stránky PHP *php.net*. Ak prešla kontrola, kombináciou `XMLaddVarLabel()`, `XMLaddSymb()` a prípadných špeciálnych prípadov sa zapíšu do objektu `XML` pomocou funkcií jeho triedy 
potrebné parametre. Nakoniec, ak nedošlo k chybe, sa na štandardný výstup vypíše reprezentáciu programu v XML.
Všetky chybové hlásenia sa vypíšu na štandardný chybový výstup. 