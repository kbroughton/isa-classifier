See ml challenge at praetorian.com | careers | challenges

Start with praet_ml_challenge_dev.ipynb to see how data is aquired
If it is your first time using the notebook, aquire some pre-fetched data since fetching is slow
Buy running the Fetch Data cell.

mnb-parameter-tuning.ipynb - tuning hyperparamters


Notes
isa-classifier/etl.py is symlinked into subdirectories for easy loading.
on a user's container's first boot, kube fetches a release from github with the notebooks.
To refresh with a newer release, remove the ~/.copied marker file.  Then stop and restart the server from the jupyterhub UI.

TODO

Understand why hexdump.js values always have leading 0's.  My input can start with anything it seems.
Complete translating hexdump.js to hexdump.py


mnb-parameter-tuning.ipynb - why does training error vary with hyperparameters, but dev error does not except when vocabulary changes?

Multi-classifier.ipynb - finish comparing other classifiers


Build word2vec tokenizer

Build CNN / RNN from first principles (numpy)

Build tensorflow version of sklearn solution

Create separate minimal container (miniconda) with etl.py to gather data offline (may need extra IPs) if we need more data



