#!/bin/bash

# this script assumes that `python` is `python3`.
# why would it be anything else ;)

# this script must be called with *two* positional arguments:
# $1: the name of the class, in an exact match as part of 
# $assignment_num: give the number of the homework to be graded, e.g. either 1 or 4 in autograde.sh DS710 1, or autograde.sh DS710 4a
#
# also, this script and the code it calls depend on two environment variables being set:
#   1.  coursenum_REPO_LOC, giving the folder for the git repo for this class
#   2.  CANVAS_CREDENTIAL_FILE , giving the path *and name* of a file containing Python code which defines API_KEY for Canvas.

################
# ready???? go!!!
# https://www.youtube.com/watch?v=26NTZpAiPyE&ab_channel=PrestonWardCondra


# first, get the directory of this script, because other useful things are in there, too.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

timeout_duration="30" # number of seconds.  this should probably be an argument to this script.

# https://stackoverflow.com/questions/3474526/stop-on-first-error
set -e

# https://stackoverflow.com/questions/592620/how-can-i-check-if-a-program-exists-from-a-bash-script
command -v timeout >/dev/null 2>&1 || { echo >&2 "'autograde.sh' requires 'timeout' but it's not installed.  On MacOS, install using 'brew install coreutils'.  Aborting."; exit 1; }



if [ -z $1 ];
	then
		# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash
		echo "a first positional argument is required, indicating the course number.  e.g. the 'DS710' or 'DS150' in 'autograde.sh DS710 1', or 'autograde.sh DS150 4a'";
		exit 1 # https://stackoverflow.com/questions/1378274/in-a-bash-script-how-can-i-exit-the-entire-script-if-a-certain-condition-occurs
fi

course_number=$1
COURSE_REPO_LOC="$1_REPO_LOC"
echo "course repo location being used: ${!COURSE_REPO_LOC}"

if [ -z $2 ];
	then
		# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash
		echo "a second positional argument is required, indicating the number of the assignment.  e.g. the '1' or '4' in 'autograde.sh DS710 1', or 'autograde.sh DS150 4a'";
		exit 1 # https://stackoverflow.com/questions/1378274/in-a-bash-script-how-can-i-exit-the-entire-script-if-a-certain-condition-occurs
fi

assignment_num=$2

if [ -z ${COURSE_REPO_LOC+x} ];
	then
		# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash
		echo "environment variable '$COURSE_REPO_LOC' unset.  set it to the path of the github repo for '$course_number'.";
		exit 1 # https://stackoverflow.com/questions/1378274/in-a-bash-script-how-can-i-exit-the-entire-script-if-a-certain-condition-occurs
fi




################## check if there are even any files to grade.  

if test -n "$(find ./ -maxdepth 1 -name '*.py' -print -quit)"
then
    echo "autograding $course_number assignment $assignment_num using autograding files from '$COURSE_REPO_LOC'";
else
	echo "no python files found in your current directory.  are you in the correct directory?"
    exit -42
fi




################3
# move pdf's to make view less shitty
echo "moving pdf's to ./_reflections"
python3 ${SCRIPT_DIR}/move_reflections.py


##########
# copy necessary data files

# if the assignment has a spec for needed data files
function copy_data_files {
  dfiles="${!COURSE_REPO_LOC}/_course_metadata/necessary_data_files/${assignment_num}.txt"
  if test -f $dfiles; then
  	#echo "copying data files as described in $dfiles"
  	while IFS="" read -r p || [ -n "$p" ]
  	do
  		cp "${!COURSE_REPO_LOC}/Lesson_$assignment_num/$p" ./
  		#echo "    copied " "${!COURSE_REPO_LOC}/Lesson_$assignment_num/$p"
  	done < $dfiles
  fi
}






################
# run the pre-submission checker for every submitted file


# copy the checker file to this folder.  this is because the checker imports the file, and if it's not in the same location, things break.
prechecker=${!COURSE_REPO_LOC}/Lesson_${assignment_num}/assignment${assignment_num}_checker.py
echo "grading using pre-submission checker $prechecker"

cp "$prechecker" ./


# copy the solutions file to this folder.  this is because the checker imports the file, and if it's not in the same location, things break.
solutionsfile=${!COURSE_REPO_LOC}/Lesson_${assignment_num}/assignment${assignment_num}_sol.py
echo "using instructor solution from file ${solutionsfile}"

cp "$solutionsfile" ./


# make a directory into which to store the results of running the tests
if [ ! -d ./_autograding/pre_checker_results ]; then
	rm -rf ./_autograding/pre_checker_results
    mkdir -p ./_autograding/pre_checker_results
fi

set +e
# $() needed in case filenames have spaces.  weird characters still likely to break this.


OIFS="$IFS"
IFS=$'\n'

for filename in `find . -type f -name "*.py"`; do
# for i in $(ls *.py); do
	# about the 2>, see https://stackoverflow.com/questions/14246119/python-how-can-i-redirect-the-output-of-unittest-obvious-solution-doesnt-wor/22710204

	if [[ "$filename" != *"checker.py" ]] && [[ "$filename" != *"sol.py" ]]; then
	  echo "$filename"
	  if [[ "$filename" != *"assignment${assignment_num}"*".py" ]]; then
	  	echo "incorrectly named submission, $filename"
	  	continue
	  fi

	  copy_data_files

	  # using SIGINT so that we get a nice traceback
	  # using --full-trace so that the student / we get a stack trace to find what was running when it was killed.
	  timeout  --signal=SIGINT --foreground "$timeout_duration"s pytest --full-trace --junitxml=./_autograding/pre_checker_results/"$filename".xml "assignment${assignment_num}_checker.py" "$filename" 1> ./_autograding/pre_checker_results/"$filename"_their_output.out
	  # timeout returns 124 if the command timed out. 
	  timeout_status=$?

	  if [[ $timeout_status -eq 124 ]]; then
	  	message="🐢 checking $filename with assignment${assignment_num}_checker.py timed out after $timeout_duration seconds, and consequently generated no test results.  automatically generated result containing one failing test written instead."
	  	echo $message
	  	echo $message >> ./_autograding/pre_checker_results/"$filename"_their_output.out 
	  	python3 "${SCRIPT_DIR}"/make_timeout_xml.py ./_autograding/pre_checker_results/"$filename".xml $timeout_duration
	  fi

	fi
done #< <(find . -maxdepth 1 -type d -print0)

# remove empty files
find ./_autograding/pre_checker_results/ -name "*output.out" -size  0  -delete

mv "./assignment$assignment_num_checker.py" ./_autograding


set -e
################
# run the post-submission checker for every submitted file
postchecker="${!COURSE_REPO_LOC}/Lesson_${assignment_num}/assignment${assignment_num}_postsubmission_checker.py"
echo "grading using post-submission checker $postchecker"
cp "$postchecker" ./

if [ ! -d ./_autograding/post_checker_results ]; then
    mkdir -p ./_autograding/post_checker_results
fi

set +e
for filename in `find . -type f -name "*.py"`; do
	if [[ "$filename" != *"checker.py" ]] && [[ "$filename" != *"sol.py" ]]; then
	  echo "$filename"

	  copy_data_files

	  # using SIGINT so that we get a nice traceback
	  # using --full-trace so that the student / we get a stack trace to find what was running when it was killed.
	  timeout  --signal=SIGINT --foreground "$timeout_duration"s pytest --full-trace --junitxml=./_autograding/post_checker_results/"$filename".xml "assignment${assignment_num}_postsubmission_checker.py" "$filename" 1> ./_autograding/post_checker_results/"$filename"_their_output.out
	  # timeout returns 124 if the command timed out.  
	  # see https://stackoverflow.com/questions/38534097/bash-if-command-timeout-execute-something-else
	  timeout_status=$?

	  if [[ $timeout_status -eq 124 ]]; then
	  	message="🐢 checking $filename with assignment${assignment_num}_postsubmission_checker.py timed out after $timeout_duration seconds, and consequently generated no test results.  automatically generated result containing one failing test written instead."
	  	echo $message
	  	echo $message >> ./_autograding/post_checker_results/"$filename"_their_output.out 
	  	python3 "${SCRIPT_DIR}"/make_timeout_xml.py ./_autograding/post_checker_results/"$filename".xml $timeout_duration
	  fi

	fi

done;

# remove empty files
find ./_autograding/post_checker_results/ -name "*output.out" -size  0  -delete

set -e
mv "./assignment${assignment_num}_postsubmission_checker.py" ./_autograding


mv "./assignment${assignment_num}_sol.py" ./_autograding


####################################
# get the current student list, so that students who didn't submit can get 0's
echo 'getting current student list from Canvas, automatically'
echo "python3 "${SCRIPT_DIR}"/get_current_students.py $COURSE_REPO_LOC"
python3 "${SCRIPT_DIR}"/get_current_students.py $COURSE_REPO_LOC


#################################
# collect the results, using our friend, python
echo 'collecting and formatting'
echo "python3 "${SCRIPT_DIR}"/assignment_grade_collector.py $COURSE_REPO_LOC $assignment_num"
python3 "${SCRIPT_DIR}"/assignment_grade_collector.py $COURSE_REPO_LOC $assignment_num


echo "done.  results and artifacts in ./autograding/"
echo "put your comments in _autograding/feedback.xml, and then run 'python3 ${SCRIPT_DIR}/upload_feedback.py $1_REPO_LOC $assignment_num'"
echo "grades are written into same xml document as feedback!"