import pandas as pd
from lxml import objectify
import canvasapi
import os
from os.path import join

# inspired by
#https://stackabuse.com/reading-and-writing-xml-files-in-python-with-pandas/

repo_variable_name = "DS150_REPO_LOC"


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
        print(f'`get_current_students.py` needs an environment variable `{repo_variable_name}`, containing the full path of git repo for DS710')
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



def read_data():
    xml_data = objectify.parse('_autograding/feedback.xml')  # Parse XML data

    root = xml_data.getroot()  # Root element

    students = []
    for i in range(len(root.getchildren())):
        child = root.getchildren()[i]
        data_this_student = {subchild.tag:subchild.text for subchild in child.getchildren()}
        students.append(data_this_student)


    return students


def get_matching_assignment(course, assignment_number):
    assignments = course.get_assignments()

    matching = []

    for assignment in assignments:
        short_name = assignment.name.split(' --- ')[0]
        if short_name == f'🏠 Assignment {assignment_number}':
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


    # finally, convert to pdf
    pypandoc.convert_file(temp_filename, 'pdf', outputfile=outname, extra_args=['-V','geometry:margin=1.5cm', '--include-in-header', '_autograding/arst.tex'])

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

def upload(students, assignment):

    canvas = make_canvas()

    course_ids = get_current_course_ids(repo_variable_name)

    print(course_ids)
    course = canvas.get_course(course_ids[0]) 


    assignment = get_matching_assignment(course, assignment_number)


    dry_run = True

    import math

    for student in students:
        n = student['sortable_name']

        if n != "Hesse-Withbroe, Jack":
            continue

        print(f'processing feedback for {n}')

        if student['auto_feedback_pre'].startswith('no submission'):
            if dry_run:
                print(f'no submission from {n}, skipping')

            continue
            # q = 'no submission as of this time, feedback to give yet.  please consider submitting!'
            # if not dry_run:
            #     submission.edit(comment={'text_comment':q})
            # else:
            #     n = student['sortable_name']
            #     print(f'no submission from student {n}, giving stock feedback:\n{q}')
            


        # get their submission.  only do this if they actually submitted.  will get something either way!!!
        submission = get_matching_submission(assignment, int(student['student_id']))






        manual_feedback = student['manual_feedback']

        if not dry_run:
            submission.edit(comment={'text_comment':manual_feedback})
        else:
            print(f'DRYRUN -- would put comment in textbox:\n---\n{manual_feedback}---\n')






        p = float(student['percent_pass_pre'])
        if p<1:
            feedback_name = join('_autograding','presubmission_checker_auto_feedback.pdf')
            feedback_to_pdf(student['auto_feedback_pre'], feedback_name)
            
            if not dry_run:
                submission.upload_comment(feedback_name)
            else:
                print(f'DRYRUN -- would upload file as comment to submission, {feedback_name}')

        else:
            f = student['auto_feedback_pre']
            if not dry_run:
                submission.edit(comment={'text_comment':f})
            else:
                print(f'DRYRUN -- would put comment in submission, {f}')




        p = float(student['percent_pass_post'])
        if p<1:
            feedback_name = join('_autograding','postsubmission_checker_auto_feedback.pdf')
            feedback_to_pdf(student['auto_feedback_post'], feedback_name)
            
            if not dry_run:
                submission.upload_comment(feedback_name)
            else:
                print(f'DRYRUN -- would upload file as comment to submission, {feedback_name}')

        else:
            f = student['auto_feedback_post']
            if not dry_run:
                submission.edit(comment={'text_comment':f})
            else:
                print(f'DRYRUN -- would put comment in submission, {f}')











if __name__=="__main__":

    assignment_number = 2 # should be argv in...

    students = read_data()


    

    upload(students, assignment_number)


