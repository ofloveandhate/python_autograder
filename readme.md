# Intro

This repo contains code used for assistive autograding homework submissions, submitted through Canvas and downloaded in bulk.  It produces a csv file report on student unit test pass/fails, and a generated markdown file which can be used to give feedback.

---

# Setup

Add two environment variables to your shell login file:
1.  `$coursenum_REPO_LOC`, giving the folder for the git repo for your class, where `coursenum` should be a code like `DS150` or `MATH114`.  So a complete variable name might be `DS710_REPO_LOC`.  
2.  `$CANVAS_CREDENTIAL_FILE`, giving the path *and name* of a `.py` file containing one line of code:
```
API_KEY = "mykeyfromcanvasene4i1n24ein1o2ie3n4i1oe2n"
``` 

I use `bash`, sometimes `zsh`, and they use the same command structure.  Shells `tcsh` and `csh` are a bit different.

```
export $DS710_REPO_LOC=/path/to/folder
export $CANVAS_CREDENTIALS_FILE=/path/to/canvas_credentials.py
```

You must also install the following packages in Python:
* `pandas`
* `canvasapi`

---

# How to autograde a homework assignment using this autograder

Each assignment uses the `pytest` library for unit tests, in two blocks: one is distributed to the students, the other is kept to the instructor and never distributed.  The student submissions are passed through the unit tests, and the results tabulated into a CSV and a markdown file, which you can use to give feedback.


1. Download submissions from each section on Canvas.  If I have multiple sections, I like running autograder on one section during testing (for speed), and on multiple sections for actual processing.  To do this, I make a new directory, and copy in all submissions.
2. Move to the the folder containing the files you want to grade.
3. Run the command `autograde.sh coursenum N`. For example, `autograde.sh DS710 4a`.  That is,
  * `coursenum` matches the name of the environment variable pointing to the folder for your course content (including case)
  * `N` is the shortname of the lesson/assignment (e.g. `1` or `4a`).  
4. Hope
5. The results should be contained in a folder called `_autograding` (the _ is there to keep it at the top).
6. Inspect the results. You should see
  * `unit_test_results.csv`, for your viewing pleasure
  * `code_feedback_Section_X.md`.  
  * two results folders
  * The checkers which were executed.  
  * The data files should probably also be in here.  If not, then add code to `autograde.sh` to move them in.  
7. If satisfied, copy the feedback files to somewhere else or rename them, so that if you have to re-run the autograder, you won't lose your comments.
8. Open the submissions folder with the code in a nice text editor.  Open the feedback files in another.  Grade as you will.


---

# Necessary structure for this autograder to work

In the local folder for your course content (environment variable $DS710_REPO_LOC), you must have the following structure:

## Per-lesson files

We assume your course is set up with one folder per "Lesson", and that each lesson has one assignment.  Furthermore, each assignment has two `.py` files associated with it, with `N` being a placeholder for whatever you want:
* `Lesson_N/assignmentN_checker.py` -- contains `pytest` unittests which are distributed to the students, so that they can run the tests as they solve the problems.  Try to put as many tests in here as possible, so that the students have maximal code coverage, but without spoiling the actual coded solutions.  So, test data with solutions is golden, but a function solving the problem  should be reserved for the postsubmission checker.
* `Lesson_N/test_assignmentN_postsubmission.py` -- held privately, containing programmatic solutions to the problems.  If you distribute these, you will spoil the assignment forever.
* Any necessary data files, with arbitrary names, a list of which comes next:

These files will be copied into the working folder when you run the autograder (and then moved into a subfolder e.g. `submissions/_autograding` when autograding is complete).

## Canvas course metadata 

`$DS710_REPO_LOC` must contain a folder called `_metadata`, containing the following files:

* `canned_responses.json` -- strings to regurgitate to students, such as a "Well done!" message.
* `canvas_course_ids.json` -- a data file of the course id's, date ranges, etc for DS710.  used for automatically downloading the current student roster (using `get_current_students.py`), so that non-submitting students get an entry in the data files produced.  
* `necessary_data_files/N.txt` -- an optional file per-assignment, listing the data files needed to grade that assignment.  The files are listed relatively to `Lesson_N/`  If no file present, then that assignment doesn't need any data files to be copied out of the `Lesson_N` folder.  These files should have a trailing newline in them.  The `N` here is the same thing as the `N` in the `Lesson_N/assignmentN_*.py` naming convention.  

For examples of these, see the `example_course_repo` folder in this repo.

## Student submission requirements for this autograder to work

The student *must* submit their code to Canvas as a file upload (not an attachment to a comment, but an actual file submission for a homework assignment!).  This repo relies on a naming convention from Canvas, whereby they prepend uploaded files with name/numbers, and possibly append a sequential number in case the student submits files in a new attempt.  

#### Important notes about student submissions:

The downloading feature in this set of tools will download the most recent attached files of a base name, but only from ungraded submissions.  


---

# Files in this folder

## Source

* `autograde.sh` -- the core file, a bash script.  Run it with two arguments -- the course code, and the shortcode of the assignment.  

* `assignment_grade_collector.py` -- uses Pandas to parse the checker results files in `_autograding/pre_submission_results` and `_autograding/post_submission_results`, and turn them into the feedback files and the csv with scores.

* `get_current_students.py` -- A python file which uses your Canvas API_KEY to get the current student list.  Uses `canvas_course_ids.json`.
* `readme.md` -- this file, aren't you glad it's here 🌈


---

# Risks

* ⚠️ This autograder executes student-submitted code on your computer.  You should probably run this code in a virtual machine specially set up for this purpose, not on your precious hard drive.  There is no way of knowing if a student submitted malicious code.
* ⚠️ This autograder does not solve the problem of detecting copied code.  This only executes student code against tests and summarizes the data in a few reports.
