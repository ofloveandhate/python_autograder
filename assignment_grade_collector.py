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









def collect(path):
    """
    returns: a pandas data frame

    Parses unit test output (junit xml files) from the assistive grading tool (pytest)
    """


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
        if f.endswith('.xml') and not f.endswith('_sol.py.xml'):

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
                            # print(f'encountered test failure in case {case.name}')
                            failures.append(case)

            failure_cases.append(failures)

            auto_feedback.append(tests_to_feedback(xml, join(dirname,pyname)))


    df = pd.DataFrame({'name':name, "student_id":student_id,"file_number":file_number, 
                       'auto_feedback':auto_feedback, "num_passes":num_passes, "num_fails":num_fails, "num_errors":num_errors, 'num_tests':num_tests, 'failure_cases':failure_cases})
    df['percent_pass'] = df['num_passes']/df['num_tests']

    return df

def tests_to_feedback(xml, filepath):
    '''
    turns xml junit test report into something a student might be able to handle.  this is a hard function to write.  but at least we have junit now?
    
    returns a string.
    '''

    feedback = ''

    if xml.failures>0 or xml.errors>0:
        header = f'\nIn assistive grading, while running {xml.tests} total tests, `pytest` found \n• {xml.failures} test failures (meaning a coded logical check on the values of variables in a checker), and \n• {xml.errors} tests which ran with errors.'

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
                                    # print(f'found module thing at {i}')
                                    # print(f'\n\nARSTARST\n\n{m}')
                                    j = m[i:].find('>')
                                    m = m[:i]+'your_code'+m[i+j+1:]

                                # print(m)
                                return m

                            m = remove_module_thing(format_message(something.message))
                            why = f'\n\twith message:\n```\n{m}\n```\n'

                        failures.append(what+why)


        error_names = []
        for suite in xml:
            for case in suite:
                for something in case:
                    if isinstance(something,junitparser.junitparser.Error):
                        error_names.append(case.classname+'.'+case.name)

        # prefix each with • , and join with a newline
        to_str = lambda ell, n: f'The following tests were classified by pytest as `{n}`\n\n'+'\n\n'.join(['* '+f for f in ell]) if ell else ''

        feedback = '\n\n\n'.join([header,to_str(failures,'failure'),to_str(error_names,'error')])

    return feedback


# see https://stackabuse.com/reading-and-writing-xml-files-in-python-with-pandas/
# that's where i adapted this from.  
def feedback_xml(df):
    """
    assumes that student name is index???
    """


    from lxml import etree
    import xml.etree.ElementTree as ET

    feedback_xml = etree.Element('root')  # Create root element.  all xml starts with root.

    for row in df.index:

        student = etree.SubElement(feedback_xml, 'student') # feedback_xml is parent, row is tag name

        for column in df.columns:



            d = df[column][row]

            data_point = etree.SubElement(student,column) # student is parent, colum
            data_point.text = str(d)


    ET.indent(feedback_xml, space="\t", level=0)

    xml_data = etree.tostring(feedback_xml, encoding='utf-8')  # binary string


    with open('feedback.xml', 'w', encoding='utf-8') as f:  # Write in XML file as utf-8
        f.write(xml_data.decode('utf-8'))



def deprecated_combine_feedback(row):
    """
    a function to apply, to merge two feedbacks -- from pre and post.
    """

    if row['percent_pass_pre']==1 and row['percent_pass_post']==1:
        return "\nNice work, all automatically run tests passed!\n\n# Manual grading comments:\n\n"

    feedback = '# Manual grading comments:\n\n\n\n'
    feedback = feedback + '# Automatically generated feedback on your last submitted code'
    if row['percent_pass_pre']<1:
        feedback = feedback + '\n\n## While grading, we detected that the following issues from the provided assignment checker file:\n\n'
        feedback = feedback + row['auto_feedback_pre']

    if row['percent_pass_post']<1:
        feedback = feedback + '\n\n## While grading, we detected that the following issues from an instructor-only checker file:\n\n'
        feedback = feedback + row['auto_feedback_post']

    # put line of code indicating autograder raw score here
    return feedback



def deprecated_format_feedback(row):
    """
    a function to apply to the data frame, adding some stuff to end of the feedback
    """
    val = '\n{}\n\n{}\n'.format(row['canvas_name'],row['auto_feedback_combined'])
    val = val + '\nEnd of code feedback for {}.\n\n'.format(row['canvas_name'])
    val = val + '\n**********************\nNext student\n===================\n'
    return val


def deprecated_save_feedback(feedback, filename):
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

    grades.drop(['auto_feedback_pre','auto_feedback_post','name_pre','name_post','file_number_post','failure_cases_pre','failure_cases_post'],inplace=True,axis=1)

    grades = grades.merge(students, left_on = ['student_id'], right_on =['student_id'], how = 'right')

    grades.sort_values(by=['section','canvas_name'], inplace=True)

    # round, because all those decimal places were not helpful at all.
    grades[['percent_pass_post','percent_pass_pre','autograde_score']] = grades[['percent_pass_post','percent_pass_pre','autograde_score']].round(4)

    fname = '_autograding/checker_results.csv'
    grades.to_csv(fname)

    reformat_grades_csv(fname)


### end function definitions




def generate_auto_feedback_message(test_suite_result, pre_or_post):
    assert pre_or_post in ['pre', 'post']
    import numpy as np
    from math import isnan



    if test_suite_result == "nan":
        return "no submission"

    if test_suite_result == "":
        return f"Nice work, all tests in the {pre_or_post}-submission suite of unit tests passed!"

    return test_suite_result










##### begin actual running of code

if __name__=="__main__":
    students = get_students()


    presub = collect('_autograding/pre_checker_results')
    postsub = collect('_autograding/post_checker_results')


    grades = presub.merge(postsub, on=('student_id'), suffixes=['_pre','_post'])



    grades['auto_feedback_pre'] = grades['auto_feedback_pre'].map(lambda x: generate_auto_feedback_message(x, 'pre'),na_action = None)
    grades['auto_feedback_post'] = grades['auto_feedback_post'].map(lambda x: generate_auto_feedback_message(x, 'post'),na_action = None)

    grades['autograde_score'] = 50*grades['percent_pass_pre'] + 20*grades['percent_pass_post']  #hardcoded weights here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!



    # grab only the desired columns for the feedback, to write to csv
    # keep the feedback separate from the grades
    feedback = grades[['name_pre','auto_feedback_pre','auto_feedback_post','autograde_score','student_id']]

    
    feedback.columns = ['name', 'auto_feedback_pre', 'auto_feedback_post','raw_assistive_grading_score','student_id']
    feedback = feedback.merge(students, left_on = ['student_id'], right_on =['student_id'], how = 'right')
    

    feedback = feedback.copy()


    feedback['auto_feedback_pre'].fillna('no submission, no pre-submission unit tests executed',inplace=True)
    feedback['auto_feedback_post'].fillna('no submission, no post-submission unit tests executed',inplace=True)



    feedback['manual_feedback'] = "Instructor's manual feedback:\n\n\n"

    feedback['name'].fillna(feedback['canvas_name'].map(lambda s: ''.join([c for c in s if c.isalpha()]).lower()), inplace=True)

    import csv
    for sec in feedback.section.unique():
        this_sec = feedback[feedback.section==sec].drop(['section'],axis=1)
        sec_name = sec.strip().replace(' ','_')
        # feedback_filename = f'_autograding/code_feedback_{sec_name}.md'
        # save_feedback(this_sec, feedback_filename)
        # print(f'wrote feedback file: {feedback_filename}')


        print(f'writing xml file')
        feedback_xml(feedback)




    grades['manual_score'] = pd.NA  # make space for these in the sheet
    grades['reflection_score'] = pd.NA  # make space for these in the sheet
    grades['total_score'] = pd.NA  # make space for these in the sheet


    write_grades_to_csv(grades)









