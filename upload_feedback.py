import pandas as pd
from lxml import objectify
import canvasapi
import os
from os.path import join
import sys

# inspired by
#https://stackabuse.com/reading-and-writing-xml-files-in-python-with-pandas/



def get_repo_name_and_assignment_number():
    """
    reads environment variable name and assignment number from argv
    """
    try:
        repo_variable_name = sys.argv[1]
    except:
        raise RuntimeError(f'script `upload_feedback` is intended to be called with the name of an environment variable after the script name.  add it.  for example, `python upload_feedback DS150_REPO_LOC 4b`')

    try:
        assignment_number = sys.argv[2]
    except:
        raise RuntimeError(f'script `upload_feedback` is intended to be called with an assignment number after the script name.  add it.  for example, `python upload_feedback DS150_REPO_LOC 4b`')

    return repo_variable_name, assignment_number


def get_dry_run():
    """
    reads dry run indicator from argv
    """
    try:
        return bool(int(sys.argv[3]))
    except:
        print(f'no dry_run value used.  doing dry run.  if don\'t want dry run, put `0` as 3th argument when calling this script')
        return True



def get_key():
    cred_loc = os.environ.get('CANVAS_CREDENTIAL_FILE')
    if cred_loc is None:
        print('`get_current_students.py` needs an environment variable `CANVAS_CREDENTIAL_FILE`, containing the full path of the file containing your Canvas API_KEY, *including the file name*')
        sys.exit()

    # yes, this is scary.  it was also low-hanging fruit, and doing it another way was going to be too much work
    exec(open(os.path.join(cred_loc)).read(),locals())

    if isinstance(locals()['API_KEY'], str):
        print(f'using canvas with API_KEY as defined in {cred_loc}')
    else:
        print(f'failing to use canvas.  Make sure that file {cred_loc} contains a line of code defining a string variable `API_KEY="keyhere"`')
        sys.exit()

    return locals()['API_KEY']


def make_canvas():
    API_URL = "https://uweau.instructure.com/" # custom to UWEC. deal with it.
    return canvasapi.Canvas(API_URL, get_key())



def get_current_course_ids(repo_variable_name):
    repo_loc = os.environ.get(repo_variable_name)
    if repo_loc is None:
        print(f'`upload_feedback.py` needs an environment variable `{repo_variable_name}`, containing the full path of git repo for the class you\'re grading')
        sys.exit()

    import json
    with open(os.path.join(repo_loc, '_course_metadata/canvas_course_ids.json')) as file:
        canvas_course_info = json.loads(file.read())

    # print(canvas_course_info)
    from datetime import datetime
    for name, semester in canvas_course_info.items():
        right_now = datetime.now()

        start = datetime.strptime(semester['dates']['start'],'%Y-%m-%d')
        end = datetime.strptime(semester['dates']['end'],'%Y-%m-%d')

        if start < right_now and right_now < end:
            return semester['canvas ids']

def get_extra_grade_categories(repo_variable_name):
    repo_loc = os.environ.get(repo_variable_name)

    import json

    with open(os.path.join(repo_loc, '_course_metadata/autograding.json')) as file:
        autograding_info = json.loads(file.read())

    return autograding_info["extra_categories"]

def read_data():
    xml_data = objectify.parse('_autograding/feedback_preprocessed.xml')  # Parse XML data

    root = xml_data.getroot()  # Root element

    autograding_data = []
    for i in range(len(root.getchildren())):
        child = root.getchildren()[i]

        if child.tag.startswith('student'): # there are some non-student items in the markdown file.
            data_this_student = {child.tag:child.text for child in child.getchildren()}
            autograding_data.append(data_this_student)


    return autograding_data


def get_matching_assignment(course, assignment_number, format_string):
    assignments = course.get_assignments()

    matching = []

    is_match = lambda test_name, assignment_number: test_name.startswith(format_string.format(assignment_number))

    for assignment in assignments:

        if is_match(assignment.name, assignment_number):
            matching.append(assignment)

    if len(matching) == 0:
        raise RuntimeError(f'no  assignments match, given number: {assignment_number}')
    elif len(matching) > 1:
        raise RuntimeError(f'too many assignments match!!!  given number: {assignment_number}')
    else:
        return matching[0]



def feedback_to_pdf(feedback, outname):
    if not outname.endswith('.pdf'):
        raise RuntimeError(f'outname must end with .pdf.  You provided {outname}')


    import pypandoc



    # xml cannot have < or > in, so replace codes with the characters
    feedback = feedback.replace('&lt;','<')
    feedback = feedback.replace('&gt;','>')

    # write to a file.  there's probably a file-free way of doing this, but it's nice to have the artifact
    temp_filename = join('_autograding', 'temp_markdown.md')
    with open(temp_filename,'w') as f:
        f.write(feedback)


    autogenerate_header() # TODO factor this out, do it once

    # finally, convert to pdf
    pypandoc.convert_file(temp_filename, 'pdf', outputfile=outname, extra_args=['-V','geometry:margin=1.5cm', '--include-in-header', '_autograding/autogenerated_header.tex', '--pdf-engine','xelatex'])





def autogenerate_header():
    with open ('_autograding/autogenerated_header.tex','w',encoding='utf-8') as f:
        f.write('\\usepackage{nunito}\n\\usepackage[T1]{fontenc}\n')




def get_matching_submission(assignment, student_id):
    assert isinstance(student_id, int)



    matching = []
    for s in assignment.get_submissions():
        if s.user_id == student_id:
            matching.append(s)


    if len(matching) == 0:
        return None
    elif len(matching) > 1:
        raise RuntimeError(f'too many submissions match!!!  given number: {student_id}')
    else:
        return matching[0]


    return submission

def get_format_string(repo_variable_name):
    repo_loc = os.environ.get(repo_variable_name)
    if repo_loc is None:
        print(f'`upload_feedback.py` needs an environment variable `{repo_variable_name}`, containing the full path of git repo for DS710')
        sys.exit()

    import json
    with open(os.path.join(repo_loc, '_course_metadata/autograding.json')) as file:
        autograding_meta = json.loads(file.read())
    return autograding_meta["assignment_naming_convention"]["format_spec"]


def preprocess_feedback_xml():
    # replaces < and > with their codes, so that the markdown file is valid.  

    open_marker = '<manual_feedback>'
    close_marker = '</manual_feedback>'


    with open('_autograding/feedback.xml','r',encoding='utf-8') as f:
        feedback_as_str = f.read()

    stuff_before = feedback_as_str.split(open_marker)
    


    

    feedback = [a.split(close_marker)[0] for a in stuff_before[1:]] 
    stuff_after = [a.split(close_marker)[1] for a in stuff_before[1:]] # 


    feedback = [f.replace('<','&lt;').replace('>','&gt;') for f in feedback]


    result = stuff_before[0] # seed the loop
    for a,b in zip(feedback, stuff_after):
        result += open_marker + a + close_marker + b


    # write to an intermediate file
    with open('_autograding/feedback_preprocessed.xml','w',encoding='utf-8') as f:
        f.write(result)

    return



def report_missing_totals(autograding_data):
    missing_scores = []
    for data_this_student in autograding_data:
        if not data_this_student['auto_feedback_pre'].startswith('no submission'):
            if not data_this_student['score_given'].strip():
                missing_scores.append(data_this_student['sortable_name'])

    if missing_scores:
        raise RuntimeError('you are missing scores for the following students:\n{}\n'.format('; '.join(missing_scores)))



def upload(autograding_data, assignment_number, repo_variable_name, dry_run = True):


    report_missing_totals(autograding_data)


    canvas = make_canvas()

    course_ids = get_current_course_ids(repo_variable_name)

    if len(course_ids) != 1:
        raise RuntimeError(f'too many courses match: {course_ids}')

    course = canvas.get_course(course_ids[0])

    format_string = get_format_string(repo_variable_name)

    assignment = get_matching_assignment(course, assignment_number,format_string)


    import math

    for data_this_student in autograding_data:
        n = data_this_student['sortable_name']

        

        if data_this_student['auto_feedback_pre'].startswith('no submission'):
            if dry_run:
                print(f'no submission from {n}, skipping')

            continue
            # q = 'no submission as of this time, feedback to give yet.  please consider submitting!'
            # if not dry_run:
            #     submission.edit(comment={'text_comment':q})
            # else:
            #     n = data_this_student['sortable_name']
            #     print(f'no submission from data_this_student {n}, giving stock feedback:\n{q}')


        print(f'processing feedback for {n}')
        
        # get their submission.  only do this if they actually submitted.  will get something either way!!!
        submission = get_matching_submission(assignment, int(data_this_student['student_id']))




        manual_feedback = data_this_student['manual_feedback']

        if not dry_run:
            submission.edit(comment={'text_comment':manual_feedback})
        else:
            print(f'DRYRUN -- would put comment in textbox:\n---\n{manual_feedback}---\n')






        upload_pytest_feedback(data_this_student, submission, assignment, dry_run)


        extra_category_names = get_extra_grade_categories(repo_variable_name)

        upload_score(data_this_student, submission, assignment, extra_category_names, dry_run)


def upload_pytest_feedback(data_this_student, submission, assignment, dry_run):

    p = float(data_this_student['percent_pass_pre'])
    if p<1:
        feedback_name = join('_autograding','presubmission_checker_auto_feedback.pdf')
        feedback_to_pdf(data_this_student['auto_feedback_pre'], feedback_name)

        if not dry_run:
            submission.upload_comment(feedback_name)
        else:
            print(f'DRYRUN -- would upload file as comment to submission, {feedback_name}')

    else:
        f = data_this_student['auto_feedback_pre']
        if not dry_run:
            submission.edit(comment={'text_comment':f})
        else:
            print(f'DRYRUN -- would put comment in submission, {f}')




    p = float(data_this_student['percent_pass_post'])
    if p<1:
        feedback_name = join('_autograding','postsubmission_checker_auto_feedback.pdf')
        feedback_to_pdf(data_this_student['auto_feedback_post'], feedback_name)

        if not dry_run:
            submission.upload_comment(feedback_name)
        else:
            print(f'DRYRUN -- would upload file as comment to submission, {feedback_name}')

    else:
        f = data_this_student['auto_feedback_post']
        if not dry_run:
            submission.edit(comment={'text_comment':f})
        else:
            print(f'DRYRUN -- would put comment in submission, {f}')


def upload_score(data_this_student, submission, assignment, extra_category_names, dry_run):
    """
    data_this_student is an xml object
    submission is a canvas object
    assignment is a canvas object
    dry_run is a boolean value
    """


    def get_and_format(column,num_t):
        try:
            val = num_t(data_this_student[column])
        except:
            val = num_t(0)
        return f'{column} = {val}\n'

    get_and_format_as_int = lambda c: get_and_format(c,int)
    get_and_format_as_float = lambda c: get_and_format(c,float)

    report = 'Explanation of grade given:\n\n'

    report += get_and_format_as_float('score_from_presubmission_checker')
    report += get_and_format_as_float('score_from_postsubmission_checker')


    for cat in extra_category_names:
        report += get_and_format_as_float(cat)


    report += get_and_format_as_float('score_reflection')
    report += '\nSum: ' + get_and_format_as_float('score_given')

    total_grade = data_this_student['score_given'].strip()
    assignment_number = get_repo_name_and_assignment_number()
    dry_run = get_dry_run()

    if not total_grade:
        print(f"⚠️ Warning!  Unset score_given for {data_this_student['sortable_name']}.  This field is expected to be set by you in feedback.xml prior to uploading.  ")

    if dry_run:
        print(report)
        print(f'posted_grade will be set to: {total_grade}')
    else:
        submission.edit(comment={'text_comment':report})
        submission.edit(submission={'posted_grade':total_grade})





if __name__=="__main__":

    repo_variable_name, assignment_number = get_repo_name_and_assignment_number()
    dry_run = get_dry_run()


    preprocess_feedback_xml()


    students = read_data()

    

    upload(students, assignment_number, repo_variable_name, dry_run = dry_run)
