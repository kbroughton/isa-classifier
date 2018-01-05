See ml challenge at praetorian.com | careers | challenges

jupyter.planetkesten.com is deployed with kubernetes helm charts + Lets Encrypt for certs.

Start with praet_ml_challenge.ipynb to see how data is aquired
If it is your first time using the notebook, aquire some pre-fetched data since fetching is slow
Buy running the Fetch Data cell.


Notes
isa-classifier/etl.py is symlinked into subdirectories for easy loading.
on a user's container's first boot, kube fetches a release from github with the notebooks.
To refresh with a newer release, remove the ~/.copied marker file.  Then stop and restart the server from the jupyterhub UI.

Multi-classifier.ipynb - Most classifiers do well.  Several are tied due to the small number of errors mentioned above.

mnb-parameter-tuning.ipynb - You need a substantial number of errors for changing tuning parameters to affect the output.  If you only have 4 errors, it's difficult to flip one more or less.


TODO

Understand why hexdump.js values always have leading 0's.  My input can start with anything it seems.
Complete translating hexdump.js to hexdump.py

Currently the git repo is public.  Should make it private, but kube git volumes don't allow private creds.  Need
to deploy vault for secrets and recent fix to git-sync sidecar to fix.

Build word2vec tokenizer

Build CNN / RNN from first principles (numpy)

Build tensorflow version of sklearn solution

Add ipynb_stripout to container so notebook output isn't included in git commits

Create separate minimal container (miniconda) with etl.py to gather data offline (may need extra IPs) if we need more data

Experiment more with https://onlinedisassembler.com/static/home/index.html to examine assembly for incorrect answers and to explore binaries that could be valid for multiple ISA's.

