import pandas as pd
from arctic_fetch import getpostorcomment












df = pd.read_csv('reddust-gender.txt', sep='\t')

for row in df.iterrows():
	post = getpostorcomment("posts", row["post_id"])
