#!/bin/bash
#
# example call to this script:
# autograde.sh -a 6c -r DS710 -p 1, to use a course folder with name contained in environment variable `DS710_REPO_LOC`, to grade assignment 6c, and to skip running pre-tests (so, assuming they've been done already).
#
#
# this script assumes that `python` is `python3`.
# why would it be anything else ;)
#
#
#
# this script *must* be called with *two* named arguments:
# -r: the name of the class, in an exact match as part of 
# -a: give the number of the homework to be graded, e.g. either 1 or 4 in autograde.sh DS710 1, or autograde.sh DS710 4a
#
# there are several optional arguments:
# -p: set to anything but 0 to skip the pre-submission tests.  default is 0, so to run the tests.
# -P: set to anything but 0 to skip the post-submission tests.  default is 0, so to run the tests.
# -t: set to the time, in whole seconds, for the timeout.  default is 60.
#
# also, this script and the code it calls depend on two environment variables being set:
#   1.  course_number_REPO_LOC, giving the folder for the git repo for this class
#   2.  CANVAS_CREDENTIAL_FILE , giving the path *and name* of a file containing Python code which defines API_KEY for Canvas.

################
# ready???? go!!!
# https://www.youtube.com/watch?v=26NTZpAiPyE&ab_channel=PrestonWardCondra


# first, get the directory of this script, because other useful things are in there, too.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


# https://stackoverflow.com/questions/3474526/stop-on-first-error
set -e

# https://stackoverflow.com/questions/592620/how-can-i-check-if-a-program-exists-from-a-bash-script
command -v timeout >/dev/null 2>&1 || { echo >&2 "'autograde.sh' requires 'timeout' but it's not installed.  On MacOS, install using 'brew install coreutils'.  Aborting."; exit 1; }



# set default values for these variables.  
timeout_duration="60" # number of seconds. 
course_number="UNSET_USE_DASH_r"
assignment_num="UNSET_USE_DASH_a"
skip_pre=0
skip_post=0
run_only='*'

# get values from the options.  only single-variable option names are allowed at the moment.  deal.
while getopts ":p:P:a:r:t:u:h" opt; do
  case $opt in
    p) 
		skip_pre=1 # no matter what value is passed in, the value of the variable becomes 1.  a value must still be passed in.
    	;;
    P) 
		skip_post=1 # no matter what value is passed in, the value of the variable becomes 1.  a value must still be passed in.
    	;;
    a)
		assignment_num=$OPTARG
		;;
	t)
		timeout_duration=$OPTARG
		;;
	r)
		course_number=$OPTARG
		;;
	u)
		run_only=$OPTARG
		;;
	h)
		echo "help:"
		echo "-p anything : skip pre-tests"
		echo "-P anything : skip post-tests"
		echo "-t duration : timeout is duration seconds"
		echo "-r coursnum : use use env variable COURSNUM_REPO_LOC -- the REPO_LOC is automatically added."
		echo "-a assgnnum : grade assignment number assgnnum.  the naming convention for actual assignments is in the repo, in the _course_metadata folder."
		echo "-u filter   : run only code files matching this filter.  for example 'rasp*.py'"
		echo "-h          : this help menu"
		echo ""
		echo ""
		echo "i do hope you have a nice day, and that this tool is not a nightmare"
		exit 0
		;;
    \?) echo "Invalid option -$OPTARG" >&2
    	exit 1
    ;;
  esac

  # case $OPTARG in
  #   -*) echo "Option $opt needs a valid argument"
  #   exit 1
  #   ;;
  # esac
done



COURSE_REPO_LOC="${course_number}_REPO_LOC"
echo "course repo location being used: ${!COURSE_REPO_LOC}"

# https://superuser.com/questions/688882/how-to-test-if-a-variable-is-equal-to-a-number-in-shell
if [[ "${course_number}" == "UNSET_USE_DASH_r" ]];
	then
		echo "use a named argument, with flag -r, to specify the course number.  e.g. the '-r DS710' or '-r DS150' in 'autograde.sh -r DS710  -a 1', or 'autograde.sh -r DS150 -a 4a'.  this is used to build an environment variable name, like 'DS710_REPO_LOC'";
		exit 3 # https://stackoverflow.com/questions/1378274/in-a-bash-script-how-can-i-exit-the-entire-script-if-a-certain-condition-occurs
fi


if [[ "${assignment_num}" == "UNSET_USE_DASH_a" ]];
	then
		echo "use a named argument, with flag -a, to specify the assigment number.  e.g. the '-a 1' or '-a 4a' in 'autograde.sh -r DS710 -a 1', or 'autograde.sh -r DS150 -a 4a'";
		exit 4 # https://stackoverflow.com/questions/1378274/in-a-bash-script-how-can-i-exit-the-entire-script-if-a-certain-condition-occurs
fi



if [ -z ${COURSE_REPO_LOC+x} ];
	then
		# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash
		echo "environment variable '$COURSE_REPO_LOC' unset.  set it to the path of the github repo for '$course_number'.";
		exit 5 # https://stackoverflow.com/questions/1378274/in-a-bash-script-how-can-i-exit-the-entire-script-if-a-certain-condition-occurs
fi




################## check if there are even any files to grade.  

if test -n "$(find ./ -maxdepth 1 -name '*.py' -print -quit)"
then
    echo "autograding '$course_number' assignment '$assignment_num' using autograding files from '$COURSE_REPO_LOC', with timeout '$timeout_duration' and name filter '$run_only'";
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




# copy the solutions file to this folder.  this is because the unit tests imports the file, and if it's not in the same location, things break.
solutionsfile=${!COURSE_REPO_LOC}/Lesson_${assignment_num}/assignment${assignment_num}_sol.py
echo "using instructor solution from file ${solutionsfile}"

cp "$solutionsfile" ./



# https://superuser.com/questions/688882/how-to-test-if-a-variable-is-equal-to-a-number-in-shell
if [[ "$skip_pre" -eq 0 ]]; then

	################
	# run the pre-submission tests for every submitted file


	# copy the unit test file to this folder.  this is because the test imports the file, and if it's not in the same location, things break.
	presuite=${!COURSE_REPO_LOC}/Lesson_${assignment_num}/test_assignment${assignment_num}.py
	echo "grading using pre-submission unit tests: $presuite"

	cp "$presuite" ./


	# make a directory into which to store the results of running the tests
	if [ ! -d ./_autograding/pre_submission_results ]; then
		rm -rf ./_autograding/pre_submission_results
	    mkdir -p ./_autograding/pre_submission_results
	fi

	set +e
	# $() needed in case filenames have spaces.  weird characters still likely to break this.


	OIFS="$IFS"
	IFS=$'\n'

	for filename in `find . -type f -name "*.py" -name "${run_only}"`; do
		# about the 2>, see https://stackoverflow.com/questions/14246119/python-how-can-i-redirect-the-output-of-unittest-obvious-solution-doesnt-wor/22710204

		if [[ "$filename" != *"test_assignment${assignment_num}"*".py" ]] && [[ "$filename" != *"sol.py" ]]; then
		  echo "$filename"
		  if [[ "$filename" != *"assignment${assignment_num}"*".py" ]]; then
		  	echo "incorrectly named submission, $filename"
		  	continue
		  fi


		  copy_data_files

		  # using SIGINT so that we get a nice traceback
		  # using --full-trace so that the student / we get a stack trace to find what was running when it was killed.
		  timeout  --signal=SIGINT --foreground "$timeout_duration"s pytest --full-trace --junitxml=./_autograding/pre_submission_results/"$filename".xml "test_assignment${assignment_num}.py" "$filename" 1> ./_autograding/pre_submission_results/"$filename"_their_output.out
		  # timeout returns 124 if the command timed out. 
		  timeout_status=$?

		  if [[ $timeout_status -eq 124 ]]; then
		  	message="🐢 testing $filename with test_assignment${assignment_num}.py timed out after $timeout_duration seconds, and consequently generated no test results.  automatically generated result containing one failing test written instead."
		  	echo $message
		  	echo $message >> ./_autograding/pre_submission_results/"$filename"_their_output.out 
		  	python3 "${SCRIPT_DIR}"/make_timeout_xml.py ./_autograding/pre_submission_results/"$filename".xml $timeout_duration
		  fi

		fi
	done #< <(find . -maxdepth 1 -type d -print0)

	# remove empty files
	find ./_autograding/pre_submission_results/ -name "*output.out" -size  0  -delete

else
	echo "skipping pre-submission tests, per your request from the -p argument to this script"
fi # re: if skip_pre


set -e
################

#
#
# Run the post-submission tests
#
#
# https://superuser.com/questions/688882/how-to-test-if-a-variable-is-equal-to-a-number-in-shell
if [[ "$skip_post" -eq 0 ]]; then
	# run the post-submission unit tests for every submitted file
	postsuite="${!COURSE_REPO_LOC}/Lesson_${assignment_num}/test_assignment${assignment_num}_postsubmission.py"
	echo "grading using post-submission unit tests: $postsuite"
	cp "$postsuite" ./

	if [ ! -d ./_autograding/post_submission_results ]; then
	    mkdir -p ./_autograding/post_submission_results
	fi

	set +e
	for filename in `find . -type f -name "*.py" -name "${run_only}"`; do
		if [[ "$filename" != *"test_assignment${assignment_num}"*".py" ]] && [[ "$filename" != *"sol.py" ]]; then
		  echo "$filename"
		  if [[ "$filename" != *"assignment${assignment_num}"*".py" ]]; then
		  	echo "incorrectly named submission, $filename"
		  	continue
		  fi


		  copy_data_files

		  # using SIGINT so that we get a nice traceback
		  # using --full-trace so that the student / we get a stack trace to find what was running when it was killed.
		  timeout  --signal=SIGINT --foreground "$timeout_duration"s pytest --full-trace --junitxml=./_autograding/post_submission_results/"$filename".xml "test_assignment${assignment_num}_postsubmission.py" "$filename" 1> ./_autograding/post_submission_results/"$filename"_their_output.out
		  # timeout returns 124 if the command timed out.  
		  # see https://stackoverflow.com/questions/38534097/bash-if-command-timeout-execute-something-else
		  timeout_status=$?

		  if [[ $timeout_status -eq 124 ]]; then
		  	message="🐢 testing $filename with test_assignment${assignment_num}_postsubmission.py timed out after $timeout_duration seconds, and consequently generated no test results.  automatically generated result containing one failing test written instead."
		  	echo $message
		  	echo $message >> ./_autograding/post_submission_results/"$filename"_their_output.out 
		  	python3 "${SCRIPT_DIR}"/make_timeout_xml.py ./_autograding/post_submission_results/"$filename".xml $timeout_duration
		  fi

		fi

	done;

	# remove empty files
	find ./_autograding/post_submission_results/ -name "*output.out" -size  0  -delete
else
	echo "skipping post-submission tests, per your request from the -P argument to this script"
fi

set -e
# i used to move the unit tests and solution into _autograding, but removed it.


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
echo "put your comments in _autograding/feedback.xml, and then run 'python3 ${SCRIPT_DIR}/upload_feedback.py $COURSE_REPO_LOC $assignment_num'"
echo "grades are written into same xml document as feedback!"