#!/usr/bin/env python3



import pandas as pd
from lxml import objectify
import canvasapi
import os
from os.path import join


import argparse, sys




def parse_argv():

    parser=argparse.ArgumentParser()

    parser.add_argument("--repo_variable_name", help="the name of an environment variable containing the path to the repo / folder for the course.  this folder must contain a file at path `${$REPO_VARIABLE_NAME}/_course_metadata/canvas_course_ids.json`")
    parser.add_argument("--assignment", help="the number of the assignment to get.  for example, `6a`")
    parser.add_argument("--extension", help="the extension of the attachments to get.  for example, `pdf`.  by default, this is `*`, for everything.")
    parser.add_argument("--dest", help="the destination folder for where to save the attachments.  by default, this is `./downloaded_attachments`.")
    parser.add_argument("--dry_run", help="set whether to make this a dry run.  By default it's not a dry run.  Valid options are anything Python can interpret as a bool")
    parser.add_argument("--ignore_test_student", help="set whether to ignore the test student.  By default we do ignore.  Valid options are anything Python can interpret as a bool")
    args = parser.parse_args()

    # print(f"Args: {args}")
    # print(f"Dict format: {vars(args)}")

    if args.assignment is None:
        raise RuntimeError(f'script `download_ungraded_attachments.py` requires an argument `--repo_variable_name` with value the name of an environment variable, which points to the repo or folder for a canvas course compliant with `markdown2canvas`')

    if args.assignment is None:
        raise RuntimeError(f'script `download_ungraded_attachments.py` requires an argument `--assignment` with value the number of the assignment you want to download from.  for example, `6a`.')


    if args.extension is None:
        args.extension = '*'


    if args.dest is None:
        args.dest = './downloaded_attachments'

    if args.dry_run is None:
        args.dry_run = False
    else:
        args.dry_run = bool(args.dry_run)

    if args.ignore_test_student is None:
        args.ignore_test_student = False
    else:
        args.ignore_test_student = bool(args.ignore_test_student)

    return args






def get_key():
    cred_loc = os.environ.get('CANVAS_CREDENTIAL_FILE')
    if cred_loc is None:
        print('`download_ungraded_attachments.py` needs an environment variable `CANVAS_CREDENTIAL_FILE`, containing the full path of the file containing your Canvas API_KEY, *including the file name*')
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
        print(f'`download_ungraded_attachments.py` needs an environment variable `{repo_variable_name}`, containing the full path of git repo for the course')
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





def download_latest_ungraded_attachments(course, assignment, extension='*',dest='downloaded_attachments',ignore_test_student = True, dry_run = False):

    print(f'downloading ungraded .{extension} attachments from "{assignment.name}" to "{dest}"')
    
    try:
        import os
        os.mkdir(dest)
        print(f'made new directory "{dest}"')
    except:
        print(f're-using existing directory "{dest}"')
        


    downloaded_files = []
    no_attempts = []
    no_ungraded_submissions = []
    failed_downloads = []

    for s_per_student in assignment.get_submissions(include=['submission_history']):
        
        u = course.get_user(s_per_student.user_id)
        n = u.name
        
        if n=="Test Student" and ignore_test_student:
            continue
        
        if s_per_student.attempt is None:
            # print(f'no attempts yet for {n}')
            no_attempts.append(n)
            continue
        
        # set up a few helper functions
        is_ungraded = lambda s: (not s['grade_matches_current_submission']) or (s['entered_grade'] is None)
        is_graded = lambda s: not is_ungraded(s)
        
        if is_graded(s_per_student.submission_history[-1]):
            no_ungraded_submissions.append(n)
            continue
        # else:
        #     print(f'{n} has an ungraded submission')  
            
            
        # there's something ungraded to do
        
        from collections import defaultdict
        attachments_this_student = defaultdict(dict)
            
        for s in s_per_student.submission_history:
            attempt_number = s["attempt"]
            
            if is_graded(s):
                continue
                
            attachments = s['attachments']
            
            format_name = lambda sortable_name: ''.join([s.strip() for s in sortable_name.split(',')]).lower()
            format_downloaded_filename = lambda user_name_lower, filename,user_id,file_id: f"{user_name_lower}_{user_id}_{file_id}_{filename}"

            for a in attachments:
                filename = a['filename']
                file_id = a['id']
                url = a['url']

                if extension == '*' or filename.endswith(f'.{extension}'):
                    formatted_name = format_downloaded_filename(format_name(u.sortable_name),filename,u.id, file_id)
                    attachments_this_student[filename][attempt_number] = ( (formatted_name,url,file_id) )

        # now have a dict of their files, and the submissions they appeared in
        # so filter for just the most recent one with that name
        for filename, appearances in attachments_this_student.items():
            submission_numbers = [int(n) for n,q in appearances.items()]
            max_number = max(submission_numbers)
            z = appearances[max_number] # this variable name is terrible

            target_name = join(dest,f'{z[0]}')

            if not dry_run:
                try:
                    canvas.get_file(file=z[2]).download(location=target_name)
                    downloaded_files.append(z[0])
                except Exception as e:
                    failed_downloads.append((z))
                    print('unable to download {} from student {} with message {}'.format(z[0],n,e))


    
    manifest_loc = join(dest,'_manifest.txt')

    with open(manifest_loc,'w') as f:
        for d in downloaded_files:
            f.write(f'{d}\n')



    print('downloaded {} files, a list can be found at {}\n'.format(len(downloaded_files), manifest_loc))
    print('there were {} students with 0 attempts yet: \n\n{}\n'.format(len(no_attempts), '\n'.join(no_attempts)))
    print('there were {} students for whom all submissions are graded\n'.format(len(no_ungraded_submissions)))
    


    if len(failed_downloads)>0:

        fail_record_loc = join(dest,'_failed_downloads.txt')
        with open(fail_record_loc,'w') as f:
            for d in failed_downloads:
                f.write(f'{d[1]}\n')

        print('there were {} failed downloads.  urls for those files are at {}\n'.format(len(failed_downloads),fail_record_loc))
    

    return downloaded_files






if __name__=="__main__":

    args = parse_argv()

    repo_variable_name = args.repo_variable_name
    assignment_number = args.assignment
    extension = args.extension
    dest = args.dest
    dry_run = args.dry_run
    ignore_test_student = args.ignore_test_student

    canvas = make_canvas()

    course_ids = get_current_course_ids(repo_variable_name)

    course = canvas.get_course(course_ids[0]) 


    assignment = get_matching_assignment(course, assignment_number)

    downloaded_files = download_latest_ungraded_attachments(course, assignment, extension, dest, dry_run=dry_run, ignore_test_student=True)


