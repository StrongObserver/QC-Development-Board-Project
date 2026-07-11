import sys
from ai_edge_litert.interpreter import Interpreter

it = Interpreter(model_path=sys.argv[1])
it.allocate_tensors()
print("inputs:", it.get_input_details())
print("outputs:", it.get_output_details())
