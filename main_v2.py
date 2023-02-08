import tkinter
from tkinter import filedialog
import os
import cx_Oracle
import getpass


def search_for_file_path():
    root = tkinter.Tk()
    root.withdraw()  # use to hide tkinter window
    currdir = os.getcwd()
    tempfile = filedialog.askopenfilename(parent=root, initialdir=currdir, title='Please select a file')
    if len(tempfile) > 0:
        print("You chose: %s" % tempfile)

    return tempfile


def folder_path_for_corrected_files():
    root = tkinter.Tk()
    root.withdraw()  # use to hide tkinter window
    currdir = os.getcwd()
    tempdir = filedialog.askdirectory(parent=root, initialdir=currdir, title='Please select a directory')
    if len(tempdir) > 0:
        print("You chose: %s" % tempdir)

    return tempdir


def get_grad_date(list_of_records):
    for x in list_of_records:
        for y in x:
            if y[0] == 'DTP' and y[1] == '007':
                grad_date = y[3]

                return grad_date


############
# filetoread = search_for_file_path ()
# write_to_new_file = folder_path_for_corrected_files()
# grad_date = input('enter grad date: ')
# filetoread = 'sfrnslc_1853615.txt'
# grad_date = get_grad_date() #'20220525'
###########


def sepr8_file_sections(file_to_read):
    file_headers = []
    file_records = []
    file_footer = []

    with open(file_to_read, "r") as f:
        for x in f:
            if x.startswith('ISA|') or x.startswith('GS|'):
                x = x.strip('\n')
                file_headers.append(x)
            elif x.startswith('GE|') or x.startswith('IEA|'):
                x = x.strip('\n')
                file_footer.append(x)
            else:
                x = x.strip('\n')
                file_records.append(x)

    return file_headers, file_records, file_footer


def parse_student_records(file_records):
    record_rows_start = []
    record_rows_end = []

    for i, x in enumerate(file_records):

        if x.startswith('ST|'):
            record_rows_start.append(i)
        elif x.startswith('SE|'):
            record_rows_end.append((i + 1))

    group_records = zip(record_rows_start, record_rows_end)

    list_of_records = []

    record_number = 0
    for start, end in group_records:
        record_number += 1
        record_set = []
        for i, x in enumerate(file_records[start:end]):
            x = x.split('|')
            record_set.append(x)
        list_of_records.append(record_set)

    return list_of_records


def generate_list_problem_records(list_of_records):
    student_major_info = []

    for i, student_record in enumerate(list_of_records):
        student_fos2 = []
        if student_record[2][1] != 'EB4':
            for x in student_record:
                if x[0] == 'ENT' and x[1] == '03':
                    student_id = x[4]
                if x[0] == 'FOS' and x[1] == 'M':
                    student_fos_cipc = x[3]
                    student_fos_major = x[4]
                if x[0] == 'FOS' and x[1] == 'P' and x[3] == student_fos_cipc:
                    student_fos2.append(x[6])

            student_major_info.append(
                [i, student_record[2][1], student_id, student_fos_cipc, student_fos_major, student_fos2[0]])

    return student_major_info


def delete_records(cur, term_code, list_of_records_):
    records_to_delete = []
    for i, record in enumerate(list_of_records_):
        for line in record:
            if line[0] == 'ENT' and line[1] == '03':
                stuid = line[4]
        pidm = get_pidm(cur, stuid)
        crse_desc = get_crse_desc(cur, term_code, pidm)
        for line in record:
            if line[0] == 'FOS' and line[1] == 'M':
                if line[4].replace("'", " ") not in crse_desc:
                    x = i, crse_desc, line[4].replace("'", " "), stuid, pidm,
                    records_to_delete.append(x)
    return records_to_delete


def write_failed_record_logs(write_new_file_to, content_to_write):
    file_path = f'{write_new_file_to}/failed_records.txt'
    with open(file_path, "w") as f:
        first_line = f"These records required intervention, number of records: {len(content_to_write)}"
        print(first_line, file=f)
        for x in content_to_write:
            print(x, file=f)


def write_deleted_record_logs(write_new_file_to, content_to_write):
    file_path = f'{write_new_file_to}/deleted_records.txt'
    with open(file_path, "w") as f:
        first_line = f"These records were deleted from the submitted report, number of records: {len(content_to_write)}"
        print(first_line, file=f)
        for x in content_to_write:
            print(x, file=f)


def fix_student_record(list_of_records, record_number, grad_date):
    x = list_of_records[record_number]

    # correct ENR line update to EB4, clear expected grad date, update grad date
    if x[2][0] == 'ENR' and x[2][1] != 'EB4':
        x[2][1] = 'EB4'
        x[2][3] = ''
        x[2][4] = ''

    # add DTP row
    if x[4][0] != 'DTP':
        list_of_records[record_number].insert(4, ['DTP', '007', 'D8', grad_date])

    # correct second ENR line
    for line in x:
        if line[0] == 'ENR' and line[1] != 'EB4' and line[1] != 'EB3':
            line[1] = 'EB4'
            line[13] = grad_date

    # correct row count
    row_count = len(x)
    if x[(row_count - 1)][0] == 'SE':
        x[(row_count - 1)][1] = str(row_count)
    else:
        print('error updating row count for record number', record_number)


def fix_line_count_record_num(list_of_records):
    for i, x in enumerate(list_of_records):
        record_number_formatted = str((i + 1)).zfill(9)
        record_line_count = len(x)
        record_last_line = (len(x) - 1)

        x[0][2] = str(record_number_formatted)
        x[1][2] = str(record_number_formatted)
        x[(len(x) - 1)][1] = str(record_line_count)
        x[(len(x) - 1)][2] = str(record_number_formatted)


def parse_footer_file(file_footer):
    parsed_footer = []
    for i, x in enumerate(file_footer):
        parsed_footer.append(x.split('|'))

    return parsed_footer


def update_footer_line_count(parsed_footer, list_of_records):
    for i, x in enumerate(parsed_footer):
        if x[0] == 'GE':
            x[1] = str(len(list_of_records))


def write_submit_file(file_headers, list_of_records, file_footer, write_new_file_to):
    file_path = f'{write_new_file_to}/00111300.clr'
    with open(file_path, "w") as f:
        for x in file_headers:
            print(x, file=f)

        for x in list_of_records:
            for y in x:
                print('|'.join(y), file=f)

        for x in file_footer:
            print('|'.join(x), file=f)


# ######Database connection###########
def con_database():
    # dsn_tns = cx_Oracle.makedsn('zeus3.avc.edu', '1521', service_name='avcprod.avc.edu') # if needed, place an 'r' before any parameter in order to address special characters such as '\'.
    while True:
        try:
            connection = cx_Oracle.connect(user=getpass.getpass("Username: "), password=getpass.getpass("Password: "),
                                           dsn='AVCPROD',
                                           encoding="UTF-8")
            return connection
        except Exception as e:
            print(e)


def close_db_cur():
    cur.close()


def close_db_connection():
    connection.close()


def exit():
    close_db_cur()
    close_db_connection()
# ###### END Database connection###########


def get_crse_desc(cur, term_code, pidm):
    _query = f"select REGEXP_REPLACE(stvmajr_desc, '[^0-9A-Za-z]', ' ') \
                from shrdgmr \
                inner join stvmajr \
                on stvmajr_code = shrdgmr_majr_code_1 \
                where shrdgmr_term_code_grad = {term_code} \
                and shrdgmr_degs_code in ('AW','LC') \
                and shrdgmr_pidm = {pidm}"
    cur.execute(_query)
    query_results = [x[0] for x in cur]
    # app_data = cur.fetchall() #fetchall() fetchone()
    return query_results


def get_pidm(cur, stuid):  # stuid  900# '900013584'
    _query = f"select distinct SPRIDEN.SPRIDEN_PIDM from SATURN.SPRIDEN SPRIDEN where SPRIDEN.SPRIDEN_ID = '{stuid}' \
                    and SPRIDEN.SPRIDEN_CHANGE_IND is null"
    cur.execute(_query)
    query_results = [x[0] for x in cur]
    # app_data = cur.fetchone() #fetchall() fetchone()
    return query_results[0]  # app_data


'''def main():
    # obtain user variables
    file_to_read = search_for_file_path()
    write_new_file_to = folder_path_for_corrected_files()
    connection = con_database()
    cur = connection.cursor()
    term_code = input("Please input Term Code (ex. 202230:")

    # read file break into header records and footer
    file_headers, file_records, file_footer = sepr8_file_sections(file_to_read)
    # parse the records for processing
    list_of_records = parse_student_records(file_records)
    # get grad date from file
    grad_date = get_grad_date(list_of_records)

    # generate a list of records with an error
    problem_records = generate_list_problem_records(list_of_records)

    # write records to file for review
    write_failed_record_logs(write_new_file_to, problem_records)

    # fix the records
    problem_records = generate_list_problem_records(list_of_records)
    for x in problem_records:
        fix_student_record(list_of_records, x[0], grad_date)

    # Delete records without matching program
    records_to_delete = delete_records(cur, term_code, problem_records)

    # write records to file for review
    write_deleted_record_logs(write_new_file_to, records_to_delete)

    # fix the record line counts
    fix_line_count_record_num(list_of_records)

    # fix the footer report line count
    parsed_footer = parse_footer_file(file_footer)
    update_footer_line_count(parsed_footer, list_of_records)

    # write the corrected file to disk
    write_submit_file(file_headers, list_of_records, parsed_footer, write_new_file_to)'''


if __name__ == "__main__":
    # obtain user variables
    file_to_read = search_for_file_path()
    write_new_file_to = folder_path_for_corrected_files()
    connection = con_database()
    cur = connection.cursor()
    term_code = input("Please input Term Code (ex. 202230):")

    # read file break into header records and footer
    file_headers, file_records, file_footer = sepr8_file_sections(file_to_read)
    # parse the records for processing
    list_of_records = parse_student_records(file_records)

    # get grad date from file
    grad_date = get_grad_date(list_of_records)

    # generate a list of records with an error
    problem_records = generate_list_problem_records(list_of_records)

    # write records to file for review
    write_failed_record_logs(write_new_file_to, problem_records)

    # fix the records
    problem_records = generate_list_problem_records(list_of_records)
    for x in problem_records:
        fix_student_record(list_of_records, x[0], grad_date)

    # Delete records without matching program
    records_to_delete = delete_records(cur, term_code, list_of_records)
    for x in reversed(records_to_delete):
        #avcid = [y[4] for y in list_of_records[x[0]] if y[0] == 'ENT' and y[1] == '03']
        #major_on_report = [y[4] for y in list_of_records[x[0]] if y[0] == 'FOS' and y[1] == 'M']
        #print(x[0], x[1], avcid[0], major_on_report, x[3], x[4])
        del list_of_records[x[0]]

    # write records to file for review
    write_deleted_record_logs(write_new_file_to, records_to_delete)

    # fix the record line counts
    fix_line_count_record_num(list_of_records)

    # fix the footer report line count
    parsed_footer = parse_footer_file(file_footer)
    update_footer_line_count(parsed_footer, list_of_records)

    # write the corrected file to disk
    write_submit_file(file_headers, list_of_records, parsed_footer, write_new_file_to)





#%%
