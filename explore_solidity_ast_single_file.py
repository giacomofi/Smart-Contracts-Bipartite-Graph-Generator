from SolidityParser import SolidityParser
from SolidityLexer import SolidityLexer
from antlr4 import *
import re
from SolidityListener import SolidityListener
import csv


# Definition of the Listener class
class MyListener(SolidityListener):

    def __init__(self):  # Constructor. All the needed attributes to store information
        self.key_cons = ['if(', 'elseif{', 'for(', 'while(', 'else{']
        self.variable_names = []
        self.contracts = []
        self.libraries = []
        self.interfaces = []
        self.contract_type_variables = []
        self.library_type_variables = []
        self.interface_type_variables = []
        self.node_types = []
        self.user_defined_type_name = []
        self.function_name = None
        self.variable_names_and_types_dictionary = {}
        self.contract_and_functionsModifiers = {}
        self.function_calls_dictionary = {}
        self.event_contract = {}
        self.to_write = []
        self.actual = None

    def reset(self):  # In case do you need to reset the listener
        self.variable_names = []
        self.contracts = []
        self.libraries = []
        self.interfaces = []
        self.user_defined_type_name = []
        self.function_name = None
        self.function_calls_dictionary = {}
        self.actual = None
        self.to_write = []

    def extract_calls(self, expr):

        # Use regular expressions to extract variable names and function calls

        matches = re.findall(r'\b([A-Za-z_]\w*)\s*\(.*?\)\.(.*?)\(', expr)
        return matches

    def splitOnArithmeticOperator(self, expression):
        # Define the regex pattern to match any arithmetic symbol
        pattern = r'[-+*/%^<>]=|[-+*/%^<>=&|]'

        # Use re.split to split the expression based on the arithmetic symbol
        parts = re.split(pattern, expression)
        # Se c'e' un operatore aritmetico vuol dire che allora possiamo restituire la parte destra.
        if len(parts) > 1:
            return parts[1]
        # Altrimenti vuol dire che molto probabilmente e' stato usato un iteratore, e si usano iterator.next()
        # iterator.done() e cose simili
        else:
            return parts[0]

    def enterPragmaDirective(self, ctx:SolidityParser.PragmaDirectiveContext):
        pragma_name = ctx.pragmaName().getText()
        pragma_value = ctx.pragmaValue().getText()
        print(f"Pragma name: {pragma_name} with value: {pragma_value}")

    def remove_content_in_first_brackets(self, expression):
        # Find the position of the first '(' and ';'
        start = expression.find('(')
        end = expression.find(';')

        # Extract the function name
        function_name = expression[:start]

        return function_name

    # Ci serve per ripulire il corpo della funzione dai costrutti che analizziamo gia' in separata sede
    def remove_keyConstruct_block(self, expression, key_cons):
        # Usiamo lo stack per sapere quando dobbiamo fermarci nella pulizia dell'espressione
        stack = []
        round_stack = []
        # Cerchiamo se effettivamente c'e' un espressione da controllare
        index = expression.find(key_cons)
        trigger = False
        # Se index == -1 allora non dobbiamo controllare nulla
        if index == -1:
            return expression
        # Altrimenti procediamo con la pulizia dell'espressione
        else:
            # Dobbiamo capire se dentro l'if c'e' un corpo specifico, o una singola istruzione
            round_bracket_pos = expression[index:len(expression)].find('(')
            for i in range(round_bracket_pos + 1, len(expression)):
                round_stack.append(expression[round_bracket_pos])
                trigger_round = True
                if expression[i] == '(':
                    round_stack.append(expression[i])
                elif expression[i] == ')':
                    round_stack.pop()
                if len(round_stack) == 0 and trigger_round is True:
                    round_bracket_pos = i
            if expression[round_bracket_pos + 1] == '{':
                # Iniziamo a ripulire l'espressione proprio dalla keyword relativa al costrutto
                for i in range(index, len(expression)):
                    # Iniziamo a riempire lo stack dal corpo della funzione
                    if expression[i] == '{':
                        trigger = True
                        stack.append(expression[i])
                        # Se troviamo una parentesi graffa che chiude, vuol dire che abbiamo trovato il primo match per la
                        # rimozione dallo stack
                    elif expression[i] == '}':
                        stack.pop()
                    # Se lo stack e' completamente vuoto e il trigger e' a true, allora l'espressione da rimuovere e'
                    # completa
                    if len(stack) == 0 and trigger is True:
                        expression = expression.replace(expression[index:i], '')
                        break
                return expression
            else:
                for i in range(index, len(expression)):
                    if (expression[i] == ';'):
                        trigger = True
                    if trigger:
                        expression = expression.replace(expression[index:i + 1], '')
                        break
                return expression

    #  Dobbiamo assicurarci che la prima espressione da controllare non sia un cast.
    #  Se e' un cast dobbiamo verificare che sia un cast a Libreria, Interfaccia o Contratto
    def checkIfCast(self, expr):
        is_type = ''
        flag = False
        for _type in self.node_types:
            if _type in expr:
                flag = True
                is_type = _type
                break
        return flag, is_type

    # Le definizioni in generale sono queste
    # IOwnable, Ownable, SafeMath, Address, IERC20, ERC20, IERC2612Permit, Counters, ERC20Permit,
    # SafeERC20, FullMath, FixedPoint, ITreasury, IBondCalculator, IStaking, IStakingHelper, SGTBondDepository
    # Comunque esccludere le interfacce e le librerie porterebbe ad avere un grafo per lo più scarno
    # Perche' abbiamo bisogno di entrare nelle singole regole? Perchè dobbiamo prima capire quali sono
    # le variabili che fanno parte del subset che ci interessano e quali sono le funzioni che davvero ci servoni
    # I contratti sono questi
    # Ownable, ERC20, ERC20Permit, SGTBondDepository

    def enterContractDefinition(self, ctx: SolidityParser.ContractDefinitionContext):  # Override
        if str(ctx.children[0]) == 'abstract' or str(ctx.children[0]) == 'contract':
            if ctx.identifier() is None: # This is in case of empty definition
                pass
            else:
                self.actual = ctx.identifier().getText()  # Retrieve the identifier of the contract
                self.contracts.append(ctx.identifier().getText())
                self.node_types.append(ctx.identifier().getText())
                # print(f"Contract definition {self.actual}")
        elif str(ctx.children[0]) == 'library':
            if ctx.identifier() is None: # This is in case of empty definition
                pass
            else:
                self.actual = ctx.identifier().getText()  # Retrieve the identifier of the contract
                self.libraries.append(ctx.identifier().getText())
                self.node_types.append(ctx.identifier().getText())

        elif str(ctx.children[0]) == 'interface':
            if ctx.identifier() is None:
                pass
            else:
                self.actual = ctx.identifier().getText()  # Retrieve the identifier of the contract
                self.interfaces.append(ctx.identifier().getText())
                self.node_types.append(ctx.identifier().getText())



    def enterFunctionCall(self, ctx: SolidityParser.FunctionCallContext):
        # print("*** Entering Function Call ***")
        # print(ctx.getText())
        pass

    def exitFunctionCall(self, ctx: SolidityParser.FunctionCallContext):
        # print("*** Exiting Function Call ***")
        pass

    def enterInheritanceSpecifier(self, ctx: SolidityParser.InheritanceSpecifierContext):
        pass
        # print(f"Inheritance Definition {ctx.getText()}")

    # Just to check struct definitions
    def enterStructDefinition(self, ctx: SolidityParser.StructDefinitionContext):

        # Identificatore della struttura
        struct_identifier = ctx.identifier().getText()
        print(f"Struct identifier is: {struct_identifier}")
        # Campi definiti all'interno della struttura
        _variables = ctx.variableDeclaration()
        for v in _variables:
            print(f"Variable defined inside struct: {v.getText()}")

    # Controllo la definizione di enumerazioni all'interno del contratto
    def enterEnumDefinition(self, ctx:SolidityParser.EnumDefinitionContext):
        # Identificatore dell' enumerazion
        enum_identifier = ctx.identifier().getText()
        print(f"The enum definition is {enum_identifier}")
        # Valori definiti all'interno dell'enumerazione
        enum_values = ctx.enumValue()
        for v in enum_values:
            print(f"Value defined inside struct is {v.getText()}")


    def enterCustomErrorDefinition(self, ctx:SolidityParser.CustomErrorDefinitionContext):
        # Identificatore dell'errore
        error_identifier = ctx.identifier().getText()
        print(f"The custom error is {error_identifier}")
        error_parameters = ctx.parameterList()
        for p in error_parameters:
            print(f"Parameter of error {p.getText()}")



    # Usiamo questa funzione per vedere se effettivamente una funzione include un contratto come contratto
    def checkForContractInParameters(self, parameters):
        cleaned_param_list = (parameters.replace('(', '')).replace(')', '')
        separated_parameters = cleaned_param_list.split(',')
        for parameter in separated_parameters:
            for type in self.node_types:
                if type in parameter:
                    if self.function_name != 'constructor':
                        write = f"{self.actual}:{self.function_name[8:]}:{type}"
                        print(write)
                        self.to_write.append(write)
                    else:
                        write = f"{self.actual}:{self.function_name}:{type}"
                        print(write)
                        self.to_write.append(write)

                    break


    def enterModifierInvocation(self, ctx:SolidityParser.ModifierInvocationContext):
        # Nome del modifier
        modifier_invocation = ctx.identifier()
        # Vuol dire che il modifier e' definito successivamente all'interno del contratto stesso
        if self.contract_and_functionsModifiers.get(modifier_invocation.getText()) is None:
            target = self.actual
        else:
            target = self.contract_and_functionsModifiers.get(modifier_invocation.getText())
        # Vediamo se viene invocato nel costruttore o meno
        if self.function_name != 'constructor':
            write = f"{self.actual}:{self.function_name[8:]}:{target}:{modifier_invocation.getText()}"
        else:
            if self.contract_and_functionsModifiers.get(modifier_invocation.getText()) is None and modifier_invocation.getText() in self.node_types:
                target = modifier_invocation.getText()
                write = f"{self.actual}:{self.function_name}:{target}:No Chain"
            else:
                write = f"{self.actual}:{self.function_name}:{target}:No Chain"
            print(f"Checking constructor in modifier invocation: {write}")
        self.to_write.append(write)

    # Vediamo dove e' definito il modifier e a quale contratto e' associato
    def enterModifierDefinition(self, ctx:SolidityParser.ModifierDefinitionContext):
        self.contract_and_functionsModifiers.update({ctx.identifier().getText():self.actual})

    # Prendiamo il nome dell'evento e a quale contratto e' associato
    def enterEventDefinition(self, ctx:SolidityParser.EventDefinitionContext):
        event_name = ctx.identifier().getText()
        self.event_contract.update({event_name: self.actual})

    def enterEmitStatement(self, ctx:SolidityParser.EmitStatementContext):
        # Conontrolliamo dove viene emesso l'evento
        statement = self.remove_content_in_first_brackets((ctx.getText()).replace('emit', ''))
        # Vediamo a quale contratto appartiene l'evento
        contract_type = self.event_contract.get(statement)
        # Vediamo in quale funzione viene emesso l'evento
        if self.function_name != 'constructor':
            if self.function_name is None:# Consideriamo il caso in cui l'evento venga emesso nello scope globale
                self.function_name = 'Global'
                write = f"{self.actual}:{self.function_name}:{contract_type}:{statement}"
            else:
                write = f"{self.actual}:{self.function_name[8:]}:{contract_type}:{statement}"
        else:
            write = f"{self.actual}:{self.function_name}:{contract_type}:{statement}"
        self.to_write.append(write)


    def enterFunctionDefinition(self, ctx: SolidityParser.FunctionDefinitionContext):  # Override
        self.function_name = ctx.functionDescriptor().getText()  # Retrieve the function name
        # print(f"Entering Function: {self.function_name}")
        # Recuperiamo i modifiers. I modifiers sono da considerare come una chiamata a funzione
        # modifier_list = ctx.modifierList().getText()
        #print(modifier_list)
        # print(f"Analyzing function {self.function_name}")
        parameters = ctx.parameterList().getText()
        # Se una funzione non ha parametri, non ci interessa.
        if parameters == '()':
            pass
        # Se ha dei parametri allora dobbiamo controllare che effettivamete ci siano dei contratti come parametri
        else:
            self.checkForContractInParameters(parameters)
        # print(f"Function name {self.function_name}")
        block = ctx.block()
        if block is not None:
            # Questa e' una parte particolarmente ostica. In pratica questa parte include TUTTO il corpo della funzione
            # Questo include anche gli if, i while, i for, che noi analizziamo gia' in separata sede. No, non possiamo
            # analizzare tutto qui, perche' il blocco non contiene le strutture necessarie affinche' possiamo analizzare
            # in maniera certa le componenti. Saremmo costretti a fare analisi puramente testuali. Quindi dobbiamo
            # ripulire il blocco da tutte le parti relative ai costrutti (incluso il corpo dei costrutti). Per fare
            # questo ho implementato uno stack.
            expression = ctx.block().getText()
            # print(f"Not Cleaned: {expression}")
            for k in self.key_cons:
                pass
                expression = self.remove_keyConstruct_block(expression, k)
            #print(f"Cleaned: {expression}")
            cleaned_expression = (expression.replace('{', '')).replace('}', '')
            statement_expressions = cleaned_expression.split(';')
            if len(statement_expressions) == 2 and statement_expressions[1] == '':
                statement_expressions.pop(1)
            # Se la dimensione e' 1 vuol dire che c'e' una sola espressione da controllare
            if len(statement_expressions) == 1:
                # In questo punto dobbiamo chiarire se effettivamente dobbiamo prendere anche le chiamate
                # a contratto all'interno delle espressioni. ( Comunque presumo di si )
                # print(statement_expressions)
                self.exploringPossibleCall(statement_expressions[0])
            # Nel caso opposto abbiamo più espressioni da controllare
            else:
                for exp in statement_expressions:
                    # print(exp)
                    self.exploringPossibleCall(exp)

    def skipStatement(self, statement):
        if_pattern = r'if\s*\([^)]*\)\s*'
        match = re.search(if_pattern, statement)
        return bool(match)

    def cleanStatementFromIf(self, statement):
        # Define the regular expression pattern to match 'if' statements with general text inside the round brackets
        pattern = r'if\s*\([^)]*\)'
        # Use re.sub to replace the pattern with an empty string
        cleaned_expression = re.sub(pattern, '', statement)
        pattern = r'(?<!{)\belse\b'
        cleaned_expression = re.sub(pattern, '', cleaned_expression)
        return cleaned_expression


    def exploringPossibleCall(self, to_check):
        # print(to_check)
        possible_call = to_check.split('.')
        to_write = ""
        # Se ci sono chiamate a funzione allora esploriamo
        if len(possible_call) > 1:
            # Guardiamo se c'è un cast
            for p in possible_call:
                flag, _node = self.checkIfCast(p)
                # print(_node)
                # Se c'e' un cast gestiamo la stampa delle chiamate che vanno inserite su CSV
                if flag is True:
                    #print(f"Analyzing actual: {self.actual}")
                    #print(f"Analyzing function: {self.function_name}")
                    if self.function_name is None:
                        pass
                    else:
                        print(f'{self.actual}:{self.function_name[8:]}:{_node}', end='')
                        if self.function_name != 'constructor':
                            to_write += f"{self.actual}:{self.function_name[8:]}:{_node}:"
                        else:
                            to_write += f"{self.actual}:{self.function_name}:{_node}:"
                        for i in range(1, len(possible_call)):
                            print('->', end='')
                            to_write += f"->{possible_call[i]}"
                            print(f"{possible_call[i]}", end='')
                        print("")
                        self.to_write.append(to_write)
                # Nel caso non si tratti di un cast ci tocca controllare il tipo della variabile che sta chiamando
                # la funzione, cosa che potrebbe non essere banalissima
                else:
                    type_of_to_check = self.variable_names_and_types_dictionary.get(to_check)
                    if type_of_to_check in self.node_types:
                        print(f'{self.actual}:{self.function_name[8:]}:{type_of_to_check}', end='')
                        to_write += f"{type_of_to_check}:"
                        for i in range(1, len(possible_call)):
                            print('->', end='')
                            print(f"{possible_call[i]}", end='')
                            to_write += f"->{possible_call[i]}"
                        print("")
                        self.to_write.append(to_write)
                    elif type_of_to_check is None:
                        if 'this' in to_check:
                            type_of_to_check = self.actual
                            # Guardiamo se siamo nel costruttore
                            if self.function_name != 'constructor':
                                # Se siamo in una chiamata che non e' all'interno della funzione, allora
                                # siamo nello scope globale
                                if self.function_name is None:
                                    self.function_name = 'Global'
                                    self.to_write.append(f'{self.actual}:{self.function_name}:{type_of_to_check}')
                                else:
                                    self.to_write.append(f'{self.actual}:{self.function_name[8:]}:{type_of_to_check}')
                            else:
                                self.to_write.append(f'{self.actual}:{self.function_name}:{type_of_to_check}')
            # Se la lunghezza e' minore di 1 vuol dire che non abbiamo chiamate di nessun tipo
        else:
            pass


    def enterIfStatement(self, ctx: SolidityParser.IfStatementContext):
        #print("*** If Statement ***")
        #print(ctx.getText()) #get text returns the whole if, including condition and body.
        # We must check both condition and body.
        #expr = ctx.expression().getText()  # This returns the condition
        #print(f"Expression: {expr}")
        children = ctx.expression().getChildren()
        for c in children:
            if type(c) == SolidityParser.ExpressionContext:
                # print(c.getText())
                self.exploringPossibleCall(c.getText())
        statements = ctx.statement()  # This returns all the statements
        # Gli statements sono estremamente incasinati. Teoricamente con l'expression risaliamo solamente
        # al contenuto della condizione dell'if, ma non si capisce perchè, nello statement e' racchiuso
        # tutto l'if, inclusa condizione e corpo. Questa cosa va gestita bene
        for statement in statements:
            # Prendiamo il testo dello statement
            statement_text = statement.getText()
            #print(statement_text)
            # Questo e' il caso più facile. Ossia, non abbiamo nessun if dentro lo statement
            if not self.skipStatement(statement_text):
                # Dobbiamo iniziare a ripulire lo statement dalle parentesi.
                statement_text = (statement_text.replace('{', '')).replace('}', '')
                # print(statement_text)
                # Recuperiamo le singole espressioni dividendo per ;
                statement_expressions = statement_text.split(';')
                if len(statement_expressions) == 2 and statement_expressions[1] == '':
                    statement_expressions.pop(1)
                # Se la dimensione e' 1 vuol dire che c'e' una sola espressione da controllare
                if len(statement_expressions) == 1:
                    # In questo punto dobbiamo chiarire se effettivamente dobbiamo prendere anche le chiamate
                    # a contratto all'interno delle espressioni. ( Comunque presumo di si )
                    # print(statement_expressions)
                    self.exploringPossibleCall(statement_expressions[0])
                # Nel caso opposto abbiamo più espressioni da controllare
                else:
                    for exp in statement_expressions:
                        self.exploringPossibleCall(exp)
            else:
                # print(f"Statement with if: {(statement.getText())}")
                # print(f"Cleaned statement with if: {self.cleanStatementFromIf(statement.getText())}")
                # Puliamo lo stament dagli if e dagli else
                cleaned_statement = self.cleanStatementFromIf(statement.getText())
                # Dividiamo le espressioni in base al punto e virgola
                single_statements = cleaned_statement.split(';')
                # Rimuovo l'ultimo elemento perche' all'interno, per via dello split c'e' solo un elemento con
                # delle parentesi graffe, nessun testo.
                single_statements.pop(len(single_statements)-1)
                # Esploriamo tutte le singole espressioni
                for single in single_statements:
                    # print(single)
                    # Eliminiamo tutte le parentesi graffe dafli statement in modo tale da non corrompere l'analisi
                    self.exploringPossibleCall(single.replace('{', '').replace('}', ''))
                # I children non servono a nulla. Restituisce letteralmente la stessa cosa di statement.getText()
                #statement_children = statement.getChildren()
                #for c in statement_children:
                    #print(c.getText())

    def exitIfStatement(self, ctx: SolidityParser.IfStatementContext):
        # print("*** Exit from If statement ***")
        pass

    def enterForStatement(self, ctx: SolidityParser.ForStatementContext):
        # print("*** Entering For Statement ***")
        # Simple statement rappresenta l'assegnamento alla variabile di scorrimento
        # print(f"Simple statement is: {ctx.simpleStatement().getText()}")
        # Ricordiamoci che tutte le istruzioni da inserire nel for sono opzionali e quindi potrebbero non essercu
        if ctx.simpleStatement() is not None:
            if len(((ctx.simpleStatement().getText()).split('='))) > 1:
                rightpart_simple_statement = ((ctx.simpleStatement().getText()).split('='))[1]
                self.exploringPossibleCall(rightpart_simple_statement)
        else:
            pass
        statement = ctx.statement().getText()
        # Expression statement rappresenta la condizione di uscita dal ciclo
        if ctx.expressionStatement() is not None:
            expression_statement = ctx.expressionStatement().getText()
            rightpart_expression_statement = self.splitOnArithmeticOperator(expression_statement)
            self.exploringPossibleCall(rightpart_expression_statement)
        else:
            pass
        # Potrebbe essere necessario dover controllare anche le condizioni del for.
        # Spiegare di persona perche'
        # Expression rappresenta incremento o decremento del ciclo. Di conseguenza, questo non dobrebbe (credo)
        # essere necessaio controllarlo
        # expr = ctx.expression().getText()
        # print(f" Expression: {expr}")
        #print(f"Statement is: {statement}")
        cleaned_statement = (statement.replace("{", "")).replace("}", "")
        # Recupero tutte le singole espressioni all'interno del for
        for_statements = cleaned_statement.split('.')
        for s in for_statements:
            self.exploringPossibleCall(s)

    def exitForStatement(self, ctx: SolidityParser.ForStatementContext):
        # print("*** Exit For Statement ***")
        pass

    def enterDoWhileStatement(self, ctx: SolidityParser.DoWhileStatementContext):
        # print("*** Entering Do-While Statement ***")
        # print(ctx.getText())
        # Recuperiamo la condizione d'uscita dal while
        expression = ctx.expression().getText()
        self.exploringPossibleCall(expression)
        statement = ctx.statement().getText()
        cleaned_statement = (statement.replace("{", "")).replace("}", "")
        do_while_statements = cleaned_statement.split('.')
        for s in do_while_statements:
            self.exploringPossibleCall(s)

    def exitDoWhileStatement(self, ctx: SolidityParser.DoWhileStatementContext):
        # print("*** Exiting Do-While Statement ***")
        # print(ctx.getText())
        pass

    def enterWhileStatement(self, ctx:SolidityParser.WhileStatementContext):
        # print("*** ENTER WHILE STATEMENT ***")
        # Recuperiamo la condizione d'uscita dal while
        expression = ctx.expression().getText()
        # Vediamo se ci sono chiamate a funzione dentro l'expression
        self.exploringPossibleCall(expression)
        # Recuperiamo il contenuto del while
        statement = ctx.statement().getText()
        cleaned_statement = (statement.replace("{", "")).replace("}", "")
        while_statements = cleaned_statement.split('.')
        for s in while_statements:
            self.exploringPossibleCall(s)


    def exitWhileStatement(self, ctx:SolidityParser.WhileStatementContext):
        # print("*** EXIT WHILE STATEMENT ***")
        pass

    def exitFunctionDefinition(self, ctx: SolidityParser.FunctionDefinitionContext):  # Override
        self.function_name = None  # Reset the function name

    def enterExpressionStatement(self, ctx: SolidityParser.ExpressionStatementContext):  # Override
        #print("*** EXPRESSION STATEMENT ***")
        expression = ctx.expression()  # Expressions
        # Check if the expression represents a function call
        if isinstance(expression, SolidityParser.ExpressionContext):  # Checking the instance
            args_ = expression.functionCallArguments()
            if args_ is not None and self.function_name != 'constructor' and self.function_name is not None:  # If fucntionCallArguments contains something, we are dealing with a function call
                function_call = expression.getText()
                # print(function_call)
                self.function_calls_dictionary.update({function_call: self.function_name})
        #print("*** EXIT ***")


    def exitExpressionStatement(self, ctx: SolidityParser.ExpressionStatementContext):
        pass

    # Entriamo nella dichiarazione delle variabili (almeno una parte)
    def enterVariableDeclaration(self, ctx: SolidityParser.VariableDeclarationContext):
        #print("*** VARIABLE DECLARATION ***")
        # Recuperiamo nome e tipo delle variabili
        variable_name = ctx.identifier().getText()
        variable_type = ctx.typeName().getText()
        # print(f"Variable Declaration: {variable_name} of type {variable_type}")
        # Inseriamo le informazioni recuperate in un dizionario
        self.variable_names_and_types_dictionary.update({variable_name: variable_type})
        #print("*** EXIT ***")

    def enterVariableDeclarationStatement(self, ctx: SolidityParser.VariableDeclarationStatementContext):
        #  Onestamente non ho capito quale sia la differenza tra questa funzione e quella
        #  che consente di esplorare la dichiarazione e l'assegnamento di variabili normali
        #  Da quel che ho capito qui ci sono sia variabili non inizializzate (in alcuni casi)
        #  e variabili inizializzate.
        # print("*** VARIABLE DECLARATION STATEMENT ***")
        to_write = ""
        v = ctx.getText()
        splitted_expression = v.split('=')
        #  In questo caso specifico dovremmo prendere solo cio' che ci interessa
        #  A sinistra abbiamo la dichiarazione della variabile mentre a destra abbiamo la potenziale
        #  chiamata a contratto.
        # Se e' maggiore di uno vuol dire che abbiamo qualcosa da controllare
        if len(splitted_expression) > 1:
            # Prendiamo l'espressione a destra per vedere se c'e' un cast
            to_check = splitted_expression[1]
            # Prima di tutto vediamo se ci sono chiamate a funzione
            possible_call = to_check.split('.')
            # Se ci sono chiamate a funzione allora esploriamo
            if len(possible_call) > 1:
                # Guardiamo se c'è un cast
                flag, _node = self.checkIfCast(to_check)
                # Se c'e' un cast gestiamo la stampa delle chiamate che vanno inserite su CSV
                if flag is True:
                    if self.function_name is None:
                        pass
                    else:
                        print(f'{self.actual}:{self.function_name[8:]}:{_node}', end='')
                        if self.function_name != 'constructor':
                            to_write += f"{self.actual}:{self.function_name[8:]}:{_node}:"
                        else:
                            to_write += f"{self.actual}:{self.function_name}:{_node}:"
                        for i in range(1, len(possible_call)):
                            print('->', end='')
                            print(f"{possible_call[i]}", end='')
                            to_write += f"->{possible_call[i]}"
                        print("")
                        self.to_write.append(to_write)
                # Nel caso non si tratti di un cast ci tocca controllare il tipo della variabile che sta chiamando
                # la funzione, cosa che potrebbe non essere banalissima
                else:
                    type_of_to_check = self.variable_names_and_types_dictionary.get(to_check)
                    if type_of_to_check in self.node_types:
                        print(f'{type_of_to_check}', end='')
                        to_write += f"{type_of_to_check}:"
                        for i in range(1, len(possible_call)):
                            print('->', end='')
                            print(f"{possible_call[i]}", end='')
                            to_write += f"->{possible_call[i]}"
                        print("")
            # Se la lunghezza e' minore di 1 vuol dire che non abbiamo chiamate di nessun tipo
                        self.to_write.append(to_write)
            else:
                pass
        # print("*** EXIT ***")

    # def enterUserDefinedTypeName(self, ctx:SolidityParser.UserDefinedTypeNameContext):
    # parent = ctx.parentCtx
    # print(f"Parent: {parent.getText()}")
    # variable_type = ctx.getText()
    # if variable_type == 'Ownable' or variable_type == 'ERC20' or variable_type == 'ERC20Permit' or variable_type == 'SGTBondDepository':
    #     print(f"Type is {variable_type}")
    # # print(variable_type)
    # if variable_type not in self.user_defined_type_name and type(parent) is SolidityParser.UserDefinedTypeNameContext:
    #     self.user_defined_type_name.append(variable_type)
    #     print(f"User defined name {self.user_defined_type_name}")

    # Qui dovremmo recuperare tutte le variabili dichiarate come globali nei singoli contratti (almeno, mi sembra sia così)
    def enterStateVariableDeclaration(self, ctx: SolidityParser.StateVariableDeclarationContext):
        #print("*** STATE VARIBALE DECLARATION ***")
        # Recuperiamo nome e tipo delle variabili
        variable_name = ctx.identifier().getText()
        print(variable_name)
        variable_type = ctx.typeName().getText()
        # Inseriamo le informazioni recuperate in un dizionario
        self.variable_names_and_types_dictionary.update({variable_name: variable_type})
        # print(f"Variable Declaration: {variable_name} of type {variable_type}")
        if variable_type not in self.user_defined_type_name:
            self.variable_names.append(f"{variable_type} {variable_name}")
        # print("*** EXIT ***")

    def write_csv(self, file_name, path):
        with open(f"{result_path}/{file_name}.csv", "a") as _file:
            writer = csv.writer(_file)
            # writer.writerow(["File", "Source_Contract", "Source_Function", "Target_Contract"])
            for expr in self.to_write:
                splitter = expr.split(':')
                # print(splitter)
                if len(splitter) == 4:
                    writer.writerow([file_name, splitter[0], splitter[1], splitter[2], splitter[3]])
                else:
                    writer.writerow([file_name, splitter[0], splitter[1], splitter[2], "No chain"])


if __name__ == '__main__':
    #safeTransferFrom, allowance, transferFrom, balanceOf
    print("Type the path of your smart contract here")
    directory = input()
    print("Where do you want to save your csv? (type path here):")
    result_path = input()
# Inserire i modifiel nella logica ********************
    try:
        with open(directory, "r", encoding='utf-8') as sol_file:
            solidity_code = sol_file.read()
            sol_file.close()
    except UnicodeDecodeError:
        # If reading as UTF-8 fails, try reading as a binary file
        with open(directory, 'rb') as sol_file:
            solidity_code = sol_file.read().decode('utf-8', errors='ignore')
            sol_file.close()
        # Create an input stream from the Solidity source code
        input_stream = InputStream(solidity_code)

        # Create a lexer
        lexer = SolidityLexer(input_stream)

        # Create a token stream
        token_stream = CommonTokenStream(lexer)

        # Create a parser
        parser = SolidityParser(token_stream)

        # Parse the source code and get the AST
        ast = parser.sourceUnit()

        # Traverse the AST using the listener

        listener = MyListener()
        walker = ParseTreeWalker()  # Walker to explore the AST
        walker.walk(listener, ast)  # Exploring the AST
        # print(f"Interfaces: {listener.interfaces}")
        # print(f"Libraries: {listener.libraries}")
        # print(f"Contracts: {listener.contracts}")
        variables = listener.variable_names
        keys = listener.function_calls_dictionary.keys()
        #print(f"{file}: ***** TO WRITE IN CSV *****")
        # Writing on CSV file
        #listener.write_csv(file)
                # Writing on CSV file
        # with open("test.csv", "a") as graph_file:
        #     writer = csv.writer(graph_file)
        #     for k in keys:
        #         element = listener.function_calls_dictionary.get(k)
        #         function_name = element.split('function')[1]
        #         contract_name = k.split('.')[0]
        #         for i in variables:
        #             if contract_name in i:
        #                 if i.split(' ')[0] in listener.user_defined_type_name:
        #                     writer.writerow(
        #                         [f"{listener.actual}/{function_name}", f"{i.split(' ')[0]}/{contract_name}"])

    # Traverse the AST using the listener