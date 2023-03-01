import pandas as pd
import os
from os.path import join

import junitparser
from junitparser import JUnitXml
# first, function definitions.



def get_students():
    """
    reads the file 'student_list.csv', so that it can be used to seed the data sets
    """

    students = pd.read_csv("_autograding/student_list.csv")
    # students.set_index('student_id')
    students.infer_objects()
    return students


def process_filename(filename):
    """
    gets the student's name, id number, and the file number from the name of a file
    """
    a = filename.split('_')
    d = dict()
    d['name'] = a[0]
    d['student_id'] = a[1] if a[1] != "LATE" else a[2]
    d['file_number'] = a[2] if a[1] != "LATE" else a[3]

    return d


def get_num_passes(filepath):
    """
    computes the number of passed tests by reading the top lines of the checker output,
    namely by counting the number of .'s

    this number will be incorrect if there's screenout in the middle of the string
    this can only be prevented by capturing all warnings and printing during all tests,
    which makes the test output significantly less useful.
    """
    with open(filepath,'r') as file:
        data = file.read()


    as_lines = data.split('\n')

    topline = as_lines.pop(0)

    while len(set(topline)-set('.EF'))>0:
        if 'Warning' in topline:
            as_lines.pop(0) # the next line is a follow-on to the warning we're skipping
            topline = as_lines.pop(0)
        else:
            topline = as_lines.pop(0)

    num_fails = len(topline) - topline.count('.')
    return topline.count('.'), topline








def collect(path):

    name = []
    student_id = []
    file_number = []
    num_tests = []
    num_passes = []
    num_fails = []
    num_errors = []
    success_string = []
    failure_cases = []
    auto_feedback = []




    files = os.listdir(path)
    for f in files:
        if f.endswith('.xml'):

            dirname = os.path.dirname(f)
            pyname = os.path.basename(f[:-4])

            # do some stuff with the filename.  thanks, canvas.
            d = process_filename(f)
            name.append(d['name'])
            student_id.append(int(d['student_id']))
            file_number.append(int(d['file_number']))

            # now actually do things with the pytest output, which is in junit format
            print(f'parsing {join(path,f)}')
            xml = JUnitXml.fromfile(join(path,f))

            num_tests.append(xml.tests)
            num_fails.append(xml.failures)
            num_errors.append(xml.errors)
            num_passes.append(xml.tests-xml.failures-xml.errors)# are there other kinds of test failures?!?


            

            failures = []
            for suite in xml:
                for case in suite:
                    for something in case:
                        if isinstance(something,junitparser.junitparser.Failure):
                            print(f'encountered test failure in case {case.name}')
                            failures.append(case)

            failure_cases.append(failures)

            auto_feedback.append(tests_to_feedback(xml, join(dirname,pyname)))


    df = pd.DataFrame({'name':name, "student_id":student_id,"file_number":file_number, 
                       'feedback':auto_feedback, "num_passes":num_passes, "num_fails":num_fails, "num_errors":num_errors, 'num_tests':num_tests, 'failure_cases':failure_cases})
    df['percent_pass'] = df['num_passes']/df['num_tests']

    return df

def tests_to_feedback(xml, filepath):
    '''
    turns xml junit test report into something a student might be able to handle.  this is a hard function to write.  but at least we have junit now?
    
    returns a string.
    '''

    feedback = ''


    if xml.failures>0 or xml.errors>0:
        header = f'In assistive grading, while running {xml.tests} total tests, `pytest` found \n• {xml.failures} test failures (meaning a coded logical check on the values of variables in a checker), and \n• {xml.errors} tests which ran with errors.'





        failure_why = []
        failures = []
        for suite in xml:
            for case in suite:
                for something in case:
                    if isinstance(something,junitparser.junitparser.Failure):
                        what,why = '',''


                        what = case.classname+'.'+case.name
                        
                        if 'has no attribute' in something.message:
                            m = something.message
                            missing_name = m[m.find('has no attribute '):].replace('has no attribute ','')

                            why = f'\n\tdue to a missing variable in your code, with expected name `{missing_name}`'
                        else:
                            format_message = lambda m: '\n'.join(['\t\t'+L for L in m.split('\n')]).replace(filepath,'')

                            def remove_module_thing(m):

                                while (i := m.find('<module')) >= 0:
                                    print(f'found module thing at {i}')
                                    print(f'\n\nARSTARST\n\n{m}')
                                    j = m[i:].find('>')
                                    m = m[:i]+'your_code'+m[i+j+1:]

                                print(m)
                                return m

                            m = remove_module_thing(format_message(something.message))
                            why = f'\n\twith message:\n {m}'

                        failures.append(what+why)


        error_names = []
        for suite in xml:
            for case in suite:
                for something in case:
                    if isinstance(something,junitparser.junitparser.Error):
                        error_names.append(case.classname+'.'+case.name)

        # prefix each with • , and join with a newline
        to_str = lambda ell, n: f'The following tests were classified by pytest as `{n}`\n\n'+'\n\n'.join(['• '+f for f in ell]) if ell else ''

        feedback = '\n\n\n'.join([header,to_str(failures,'failure'),to_str(error_names,'error')])

    return feedback




def combine_feedback(row):
    """
    a function to apply, to merge two feedbacks -- from pre and post.
    """

    if row['percent_pass_pre']==1 and row['percent_pass_post']==1:
        return "\nNice work, all automatically run tests passed!\n\n# Manual grading comments:\n\n"

    feedback = '# Manual grading comments:\n\n\n\n'
    feedback = feedback + '# Automatically generated feedback on your last submitted code'
    if row['percent_pass_pre']<1:
        feedback = feedback + '\n\n## While grading, we detected that the following issues from the provided assignment checker file:\n\n'
        feedback = feedback + row['feedback_pre']

    if row['percent_pass_post']<1:
        feedback = feedback + '\n\n## While grading, we detected that the following issues from an instructor-only checker file:\n\n'
        feedback = feedback + row['feedback_post']

    # put line of code indicating autograder raw score here
    return feedback



def format_feedback(row):
    """
    a function to apply to the data frame, adding some stuff to end of the feedback
    """
    val = '\n{}\n\n{}\n'.format(row['canvas_name'],row['feedback_combined'])
    val = val + '\nEnd of code feedback for {}.\n\n'.format(row['canvas_name'])
    val = val + '\n**********************\nNext student\n===================\n'
    return val


def save_feedback(feedback, filename):
    """
    saves the feedback data frame to a file named `filename`
    """

    with open(filename,'w') as file:  # i'm not sure this needs to be here.  can remove?
        formatted = feedback.apply(format_feedback,axis=1)
        formatted.to_csv(filename,index=False,header=False)


def reformat_grades_csv(fname):
    """
    reads in an outputted csv of grades,
    and adjusts it so that it's nicely aligned.
    """
    def split_into_cols(r):
        r = r.split('"',2)
        return r[0].split(',')[:-1] + [('"'+r[1]+'"')] + r[2].split(',')[1:]


    def compute_column_sizes(as_lines):
        d = [split_into_cols(ell) for ell in as_lines[1:]] # [1:] to skip the header row
        temp_df = pd.DataFrame(data=d)
        return temp_df.applymap(lambda x: len(x)).max()

    def format_line(sizes, row):
        r = row.split('"',2)
        r = r[0].split(',')[:-1] + [('"'+r[1]+'"')] + r[2].split(',')[1:]
        d = r[0]
        s = ' '*(3-len(d))+d+',' # that 3 is the width of the index column

        for ii in range(1,len(r)):

            assert(len(sizes)==len(r)) # just cuz, let's keep it sane

            col_len = sizes[ii]+2 # 2 is the padding
            d = r[ii]

            c = ' '*(col_len-len(d)) + d +','
            s = s+c
        return s+'\n'

    with open(fname,'r') as f:
        as_lines = f.read().split('\n')
        as_lines = [ell for ell in as_lines if ell] # drop empty lines

    # format each line that's not the header line
    formatted = [as_lines[0]+',\n']+[ format_line(compute_column_sizes(as_lines),ell) for ell in as_lines[1:] if ell ]

    # write the file back to disk.
    with open(fname,'w') as f:
        for line in formatted:
            f.write(line)


def write_grades_to_csv(grades):
    """
    writes `grades` data frame to file, making some adjustments
    to the data frame first.
    """
    # grades.set_index('student_id')

    grades.drop(['feedback_pre','feedback_post','feedback_combined','name_pre','name_post','file_number_post','failure_cases_pre','failure_cases_post'],inplace=True,axis=1)

    grades = grades.merge(students, left_on = ['student_id'], right_on =['student_id'], how = 'right')

    grades.sort_values(by=['section','canvas_name'], inplace=True)

    # round, because all those decimal places were not helpful at all.
    grades[['percent_pass_post','percent_pass_pre','autograde_score']] = grades[['percent_pass_post','percent_pass_pre','autograde_score']].round(4)

    fname = '_autograding/checker_results.csv'
    grades.to_csv(fname)

    reformat_grades_csv(fname)


### end function definitions





##### begin actual running of code

if __name__=="__main__":
    students = get_students()


    presub = collect('_autograding/pre_checker_results')
    postsub = collect('_autograding/post_checker_results')


    grades = presub.merge(postsub, on=('student_id'), suffixes=['_pre','_post'])

    grades['feedback_combined'] = grades.apply(combine_feedback, axis=1)



    # grab only the desired columns for the feedback, to write to csv
    # keep the feedback separate from the grades
    feedback = grades[['name_pre','feedback_combined','student_id']]
    feedback.columns = ['name', 'feedback_combined','student_id']
    feedback = feedback.merge(students, left_on = ['student_id'], right_on =['student_id'], how = 'right')
    import csv
    for sec in feedback.section.unique():
        this_sec = feedback[feedback.section==sec].drop(['section'],axis=1)
        sec_name = sec.strip().replace(' ','_')
        save_feedback(this_sec, f'_autograding/code_feedback_{sec_name}.md')



    grades['autograde_score'] = 50*grades['percent_pass_pre'] + 20*grades['percent_pass_post']  #hardcoded weights here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    grades['manual_score'] = pd.NA  # make space for these in the sheet
    grades['reflection_score'] = pd.NA  # make space for these in the sheet
    grades['total_score'] = pd.NA  # make space for these in the sheet


    write_grades_to_csv(grades)









