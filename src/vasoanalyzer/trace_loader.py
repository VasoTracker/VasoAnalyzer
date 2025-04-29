import pandas as pd

def load_trace(file_path):
	trace = pd.read_csv(file_path)
	return trace
