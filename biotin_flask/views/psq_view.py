"""Reformats HTML reports generated by the PSQ Assay Design Software and outputs
a concise summary in a single CSV file

This module parses HTML files uploaded by the user for primer design information,
reorganizes this information and writes this information into a csv file

Either a single HTML file or multiple HTML files can be
provided.
"""

import os, io, csv, StringIO
from flask import render_template, request, flash, make_response
from werkzeug import secure_filename

from biotin_flask import app
from biotin_flask.models.utils import ParsePsy

__author__ = 'Eric Zhou'
__copyright__ = 'Copyright (C) 2017, EpigenDx Inc.'
__credits__ = ['Eric Zhou']
__version__ = '0.0.2'
__status__ = 'Production'

@app.route('/misc/psq', methods=['GET', 'POST'])
def psq():

    """Handle GET or POST requests to the psq URL.

    Form args:
        f:      (File) list of HTML files uploaded by user

    Returns:
        A CSV file.

    """

    # Render an empty form for GET request
    if request.method == 'GET':
        return render_template('psq/form.html')

    # Otherwise validate the form on a POST request and process uploaded files
    f = request.files.getlist('html')

    if not f[0]:
        flash('A required field is missing', 'alert-warning')
        return render_template('psq/form.html')

    # Throw error if any file does not have .html extension
    seq_primer = ''
    for file in f:
        filename = secure_filename(file.filename)
        filefront, extension = os.path.splitext(filename)
        if not extension == '.html':
            flash('Only .html files are allowed.', 'alert-warning')
            return render_template('psq/form.html')

        # Check if 'FS' or 'RS' is in the file name
        if filefront[-3:-1] == 'FS':
            seq_primer = 'FS'
        elif filefront[-3:-1] == 'RS':
            seq_primer = 'RS'
        elif filefront[-2:] == 'FS':
            seq_primer = 'FS'
        elif filefront[-2:] == 'RS':
            seq_primer = 'RS'

    # Begin cleaning and parsing the html file
    clean = []
    output = []
    p = ParsePsy() # ParsePsy is a class Eric wrote in utils.py that parses the html file
    for index, file in enumerate(f):
        try:
            # Convert file into string
            html = ''
            for line in file:
                html = html + line

            # Let ParsePsy() clean the html
            p.feed(html)
            clean.append(p.data)
            # Reset ParsePsy()
            p.data = []
            p.close()

            # Begin parsing for data
            data = []
            counter = 0
            neighbor = 0

            print clean
            for item in clean[index]:
                print item
                if neighbor > 0:
                    data.append(item)
                    neighbor -= 1
                    continue

                if counter == 0:
                    # Look for Assay Name
                    if item.replace(' ', '') == 'AssayName':
                        neighbor = 1
                        counter += 1

                elif counter == 1:
                    # Look for Description (Gene Name)
                    if item == 'Description':
                        neighbor = 1
                        counter += 1

                elif counter == 2:
                    # Look for Score:
                    if item.split()[0] == 'Score:':
                        data.append(item.split()[1])
                        counter += 1

                elif counter == 3:
                    # Look for F1 Primer
                    if item == 'F1':
                        neighbor = 4
                        counter += 1

                elif counter == 4:
                    # Look for R1 Primer
                    if item == 'R1':
                        neighbor = 4
                        counter+=1

                elif counter == 5:
                    # Look for S1 Primer
                    if item == 'S1':
                        neighbor = 4
                        counter += 1

                elif counter == 6:
                    # Look for Amplicon Length
                    if item.replace(' ', '') == 'Ampliconlength':
                        neighbor = 1
                        counter += 1

                elif counter == 7:
                    # Look for Amplicon %GC
                    if item.replace(' ', '') == 'Amplicon\r\n%GC':
                        neighbor = 1
                        counter += 1

                elif counter == 8:
                    break

            if len(data) != 17:
                flash('The uploaded file(s) are not in the correct format', 'alert-warning')
                return render_template('psq/form.html')
            output.append(data)
        except:
            flash('There was an error while reading file ' + secure_filename(file.filename), 'alert-warning')
            return render_template('psq/form.html')

    """
    data[0] = Assay ID
    data[1] = Gene
    data[2] = Assay Design Score
    data[3] = Primer Sequence (FP)
    data[4] = Length (FP)
    data[5] = Tm (FP)
    data[6] = GC% (FP)
    data[7] = Primer Sequence (RP)
    data[8] = Length (RP)
    data[9] = Tm (RP)
    data[10] = GC% (RP)
    data[11] = Primer Sequence (FS)
    data[12] = Length (FS)
    data[13] = Tm (FS)
    data[14] = GC% (FS)
    data[15] = Amplicon Size
    data[16] = Amplicon GC%
    """

    # Prepare csv printer
    dest = StringIO.StringIO()
    writer = csv.writer(dest)

    if request.form.get('output-format') == 'default':

        # Print header
        writer.writerow( ["NGS#", "Gene", "Assay ID", "Length", "Tm", "GC%", "Amplicon GC%",
                          "Amplicon size", "Assay Design Score", "Amplicon coordinates (GRCm38/mm10)",
                          "Strand", "# CpG", "# SNP", "Primer ID", "Primer Sequences", "Ta",
                          "Mg2+", "Note"] )

        # Loop through output
        row = [''] * 18
        for file in output:
            row[1] = file[1] # Gene
            row[2] = file[0] # Assay ID
            row[3] = file[4] # Length (FP)
            row[4] = file[5] # Tm (FP)
            row[5] = file[6] # GC% (FP)
            row[6] = file[16] # Amplicon GC%
            row[7] = file[15] # Amplicon Size
            row[8] = file[2] # Amplicon Design Score
            row[13] = file[0] + 'FP' # Primer ID (FP)
            row[14] = file[3] # Primer Sequence (FP)
            writer.writerow( row )
            row = [""] * 17
            row[3] = file[8] # Length (RP)
            row[4] = file[9] # Tm (RP)
            row[5] = file[10] # GC% (RP)
            row[13] = file[0] + 'RP' # Primer ID (RP)
            row[14] = file[7] # Primer Sequence (RP)
            writer.writerow(row)
            row = [""] * 17
            row[3] = file[12] # Length (FS)
            row[4] = file[13] # Tm (FS)
            row[5] = file[14] # GC% (FS)
            row[13] = file[0] + seq_primer # Primer ID (FS)
            row[14] = file[11] # Primer Sequence (FS)
            writer.writerow(row)
            row = [""] * 18

        # Make response
        response = make_response(dest.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=result.csv"
        return response

    if request.form.get('output-format') == 'oligo-order':
        well_character = 'A'
        well_number = 1

        row = [""] * 7
        writer.writerow(row)
        writer.writerow(row)
        writer.writerow(["Well", "Primer ID", "Primer Sequences", "", "Well", "Primer ID", "Primer Sequences"])

        for file in output:
            row[0] = well_character + str(well_number)
            row[1] = file[0] + 'FP'
            row[2] = file[3]
            row[4] = well_character + str(well_number)
            row[5] = file[0] + 'RP'
            row[6] = file[7]
            writer.writerow(row)
            row = [""] * 7

            # Increment the well number, e.g. A1 to A2 or A12 to B1
            if well_number < 13:
                well_number += 1
            else:
                well_number = 1
                well_character = chr(ord(well_character) + 1)

        # Make response
        response = make_response(dest.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=result.csv"
        return response