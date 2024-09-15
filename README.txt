README

TODO:
- need to work on stockanalyzer.py
- add more stock data in YFHandler and news/press release
- Need to fix ThreadManager, it's not capturing messages properly
	- _combine_messages is fixed but it's still not recording the 2nd user prompt


file management:
- Get the file with the last name on list (all files), and then group by max createdate
- store shared files on Supabase
- write_to_file not working  FileNotFoundError: [Errno 2] No such file or directory: 'images/file-dMqccidbrEle3LictfoNcw31.png'
- get_last_message is working fine now, but it's not capturing user messages for some reason

1. Local
2. file config
3. File in OpenAI


2 models
- model A: quantitative analysis
- model B: qualitative analysis
- model C: proofread