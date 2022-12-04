import re 

class Calculator:
    def __init__(self):
        self.expression = ""
        self.tokens = []
        self.result = 0
        self.prev_operator = None

    def calculate(self, expression):
        # remove all whitespace from the expression
        self.expression = expression.replace(" ", "")
        match = re.fullmatch(r'\d+(?:(\+|\-|\*|\/|plus|minus|times|dividedby)\d+)*', self.expression)

        # if there is no match, return None
        if match is None:
            return None
        # use a regular expression to match numbers, arithmetic operators, and
        # words for the operators in the expression string
        self.tokens = re.findall(r'(\d+|[\+\-\*\/]|plus|minus|times|dividedby)', self.expression)

        # initialize the result to the first number in the expression
        self.result = int(self.tokens[0])

        # iterate over the tokens in the expression
        for token in self.tokens[1:]:
            # if the token is a number, set it as the current number
            if token.isdigit():
                current_num = int(token)
            else:
                # if the token is a word for an operator, set the token to
                # the corresponding symbol
                if token == "plus":
                    token = "+"
                elif token == "minus":
                    token = "-"
                elif token == "times":
                    token = "*"
                elif token == "dividedby":
                    token = "/"

                # if the previous operator was not set, set the previous
                # operator to the current token and continue
                if self.prev_operator is None:
                    self.prev_operator = token
                    continue

            # otherwise, perform the previous operation on the result
            # and the current number
            if self.prev_operator == "+":
                self.result += current_num
            elif self.prev_operator == "-":
                self.result -= current_num
            elif self.prev_operator == "*":
                self.result *= current_num
            elif self.prev_operator == "/":
                self.result /= current_num

            # set the previous operator to the current token
            self.prev_operator = None

        # return the final result
        return self.result

Calculator().calculate('1 plus 2')