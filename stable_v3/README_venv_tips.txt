How to Always Start in Your Python venv (and Avoid (base) Issues)
===============================================================

1. **Turn off conda's auto-activation of base**
   If you ever used conda, run this once:
   conda config --set auto_activate_base false

2. **Always activate your venv when you open a new terminal**
   cd /Users/erhangocmez/testnet_feed_project
   source venv/bin/activate
   # You should see (venv) in your prompt

3. **(Optional) Add a shell alias for convenience**
   Add this to your ~/.zshrc (or ~/.bashrc):
   alias btcfeed='cd /Users/erhangocmez/testnet_feed_project && source venv/bin/activate'
   # Then just type 'btcfeed' in any new terminal

4. **(Optional) VS Code: Set the Python interpreter to venv**
   - Cmd+Shift+P → "Python: Select Interpreter" → choose venv/bin/python
   - VS Code will always use your venv for this project.

5. **Never run 'conda activate base' unless you need it for another project**

6. **(Optional) Add a note to your project README**
   # How to start
   source venv/bin/activate
   python app.py

Summary:
- Always activate venv before running anything.
- Use an alias for convenience.
- Turn off conda's auto-activation.
- Set your editor to use the venv interpreter. 