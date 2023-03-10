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


    df = pd.DataFrame({'name_from_submitted_file':name, "student_id":student_id,"file_number":file_number,
                       'auto_feedback':auto_feedback, "num_passes":num_passes, "num_fails":num_fails, "num_errors":num_errors, 'num_tests':num_tests, 'failure_cases':failure_cases})
    df['percent_pass'] = df['num_passes']/df['num_tests']

    return df

def tests_to_feedback(xml, filepath):
    '''
    turns xml junit test report into something a student might be able to handle.  this is a hard function to write.  but at least we have junit now?

    returns a string.
    '''


    # breakpoint()

    feedback = ''

    header = f'\n# Auto-generated code feedback\n\nProcessed during assistive grading, from    \n`{xml.filepath}`'

    if xml.failures>0 or xml.errors>0:
        header += f'While running {xml.tests} total tests, `pytest` found:\n\n* {xml.failures} test failures (meaning a coded logical check on the values of variables in a checker), and \n* {xml.errors} tests failed due to errors.'
        failure_why = []
        failures = []
        for suite in xml:
            for case in suite:
                for something in case:
                    if isinstance(something,junitparser.junitparser.Failure):
                        what,why = '',''


                        what = f'`{case.classname}.{case.name}`'

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

                        failures.append(f'{what}\n{why}')


        error_names = []
        for suite in xml:
            for case in suite:
                for something in case:
                    if isinstance(something,junitparser.junitparser.Error):
                        error_names.append(case.classname+'.'+case.name)

        # prefix each with `* `, and join with a newline
        to_str = lambda ell, n: f'The following tests were classified by pytest as `{n}`\n\n'+'\n\n'.join(['* '+f for f in ell]) if ell else ''

        feedback = '\n\n\n'.join([header,to_str(failures,'failure'),to_str(error_names,'error')])


    else: # no errors or failures!!! i think all tests passed.

        feedback = '\n\n\n'.join([header,"Nice work, all tests in this suite of unit tests passed!\n"])

    return feedback


# see https://stackabuse.com/reading-and-writing-xml-files-in-python-with-pandas/
# that's where i adapted this from.
def feedback_xml(df,filename):
    """
    assumes that student name is index???
    """


    from lxml import etree
    import xml.etree.ElementTree as ET

    feedback_xml = etree.Element('root')  # Create root element.  all xml starts with root.

    instructions = etree.SubElement(feedback_xml, f'InstructionsForInstructor')
    instructions.text = "todo.  write instructions here."

    for row in df.index:

        student = etree.SubElement(feedback_xml, f'student{row}') # feedback_xml is parent, row is tag name

        for column in df.columns:



            d = df[column][row]

            data_point = etree.SubElement(student,column) # student is parent, colum
            data_point.text = str(d)


    ET.indent(feedback_xml, space="\t", level=0)

    xml_data = etree.tostring(feedback_xml, encoding='utf-8')  # binary string


    with open('_autograding/feedback.xml', 'w', encoding='utf-8') as f:  # Write in XML file as utf-8
        f.write(xml_data.decode('utf-8'))






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

    grades.drop(['auto_feedback_pre','auto_feedback_post','name_from_submitted_file','file_number_post','failure_cases_pre','failure_cases_post'],inplace=True,axis=1)

    grades = grades.merge(students, left_on = ['student_id'], right_on =['student_id'], how = 'right')

    grades.sort_values(by=['section','sortable_name'], inplace=True)

    # round, because all those decimal places were not helpful at all.
    grades[['percent_pass_post','percent_pass_pre','total_assistive_grading_score','score_from_presubmission_checker','score_from_postubmission_checker']] = grades[['percent_pass_post','percent_pass_pre','total_assistive_grading_score','score_from_presubmission_checker','score_from_postsubmission_checker']].round(3)

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

    return test_suite_result



def process_feedback_and_grades(feedback_and_grades):
    feedback_and_grades = feedback_and_grades.copy()  # stupid warnings cause so much headache.  silence!


    feedback_and_grades['auto_feedback_pre'].fillna('no submission, no pre-submission unit tests executed',inplace=True)
    feedback_and_grades['auto_feedback_post'].fillna('no submission, no post-submission unit tests executed',inplace=True)


    # print(feedback_and_grades.columns)
    # feedback_and_grades['name'].fillna(feedback_and_grades['sortable_name'].map(lambda s: ''.join([c for c in s if c.isalpha()]).lower()), inplace=True)

    # feedback_and_grades = feedback_and_grades[['name', 'percent_pass_pre','percent_pass_post', 'auto_feedback_pre', 'auto_feedback_post','total_assistive_grading_score','student_id']]
    # reorder the columns to keep grades together.


    def default_feedback_message(row):
        if row['auto_feedback_pre'].startswith('no submission'):
            return 'no submission'

        else:
            n = row['sortable_name']
            return f"\n\nInstructor's manually written feedback for {n}:\n\n\n## Code\n\n*\n\n## Reflection\n\nThank you for your thoughtful reflection.\n\n---\n\n\n"


    feedback_and_grades['manual_feedback'] = feedback_and_grades.apply(default_feedback_message, axis=1) # TODO this should be read from a course meta


    feedback_and_grades['xml_spacer_end'] = feedback_and_grades['sortable_name'].map(lambda s: f'\n\n------------\nEnd feedback_and_grades for {s}\n---------------\n\n')
    feedback_and_grades['xml_spacer_begin'] = feedback_and_grades['sortable_name'].map(lambda s: f'\n\n------------\nBegin feedback_and_grades for {s}\n---------------\n\n')

    new_column_order = [feedback_and_grades.columns[-1]]
    new_column_order.extend(feedback_and_grades.columns[:-1])

    feedback_and_grades = feedback_and_grades[new_column_order]

    xml_feedback_filename = join('_autograding','feedback.xml')
    print(f'writing xml file {xml_feedback_filename}')
    feedback_xml(feedback_and_grades, filename=xml_feedback_filename)



def additional_processing_grades(grades):




    grades['auto_feedback_pre'] = grades['auto_feedback_pre'].map(lambda x: generate_auto_feedback_message(x, 'pre'),na_action = None)
    grades['auto_feedback_post'] = grades['auto_feedback_post'].map(lambda x: generate_auto_feedback_message(x, 'post'),na_action = None)


    # TODO hardcoded weights here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    grades['score_from_presubmission_checker'] = 45*grades['percent_pass_pre']
    grades['score_from_postsubmission_checker'] = 45*grades['percent_pass_post']

    # combine
    grades['total_assistive_grading_score'] =  (grades['score_from_presubmission_checker'] +  grades['score_from_postsubmission_checker']).round(3)

    #grades['score_instructor_discretion'] = '   '  # make space for these in the sheet
    grades['score_reflection'] = '   '  # make space for these in the sheet
    grades['score_given'] = '   '  # make space for these in the sheet


    # change some names of columns
    grades.rename(columns={"name_from_submitted_file_pre": "name_from_submitted_file"},inplace=True)

    grades.drop(["name_from_submitted_file_post"],inplace=True,axis=1)

    return grades



##### begin actual running of code

if __name__=="__main__":
    students = get_students()


    presub = collect('_autograding/pre_checker_results')
    postsub = collect('_autograding/post_checker_results')

    grades = presub.merge(postsub, on=('student_id'), suffixes=['_pre','_post'])

    additional_processing_grades(grades)

    feedback_and_grades = grades.copy()

    # after this line \/ \/, we'll have empty rows for students who didn't submit.
    feedback_and_grades = feedback_and_grades.merge(students, left_on = ['student_id'], right_on =['student_id'], how = 'right')



    # import csv
    # for sec in feedback_and_grades.section.unique():
    #     this_sec = feedback_and_grades[feedback_and_grades.section==sec].drop(['section'],axis=1)
    #     sec_name = sec.strip().replace(' ','_')
    #     # feedback_filename = f'_autograding/code_feedback_{sec_name}.md'
    #     # save_feedback(this_sec, feedback_filename)
    #     # print(f'wrote feedback_and_grades file: {feedback_filename}')



    process_feedback_and_grades(feedback_and_grades)

    write_grades_to_csv(grades)
