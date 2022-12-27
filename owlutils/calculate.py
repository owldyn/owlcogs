import re 

class Calculator:
    def __init__(self):
        self.expression = ""
        self.tokens = []
        self.result = 0
        self.prev_operator = None
        self.word_mapping = {
            "plus": "+",
            "minus": "-",
            "times": "*",
            "multipliedby": "*",
            "dividedby": "/",
            "tothepowerof": "^",
            "x": "*",
        }

    def calculate(self, expression):
        # remove all whitespace from the expression
        expression = expression.replace(" ", "").lower()
        match = re.fullmatch(r'\d+(?:(\+|\-|\*|\/|plus|minus|times|dividedby|x|multipliedby)\d+)*', expression)

        # if there is no match, return None
        if match is None:
            return None
        # replace words with operators
        for word, operator in self.word_mapping.items():
            expression = expression.replace(word, operator)
        # evaluate the expression
        result = eval(expression) #pylint: disable=eval-used

        # return the final result
        return result

