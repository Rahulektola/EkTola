### FAQs to solve common merge issues.
---
## 1. Merge backend to frontend without deleting any frontend files (keep frontend files).
 # SOLUTION:
    1. switch to frontend branch:
    '''
    git checkout frontend
    '''

    2. Merge without the autocommit that git does by default (do this to loccally fix merge issues first):
    '''
    git merge backend --no-commit
    '''

    3. Restore Deleted Frontend Files (Because merge might delete files):
    '''
    git checkout frontend -- .
    '''

    4. Stage and Commit the Merge:
    '''
    git add .
    git commit -m "Merged backend into frontend without deleting frontend files"
    '''
    FINISH

---