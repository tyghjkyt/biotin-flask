import os, tempfile, pysam
from flask import render_template, request, flash
from werkzeug import secure_filename
from collections import OrderedDict

from biotin_flask import app
from biotin_flask.models.utils import SamUpload
from biotin_flask.models.pysam_ext import get_refbase

@app.route('/sam/pileup', methods=['GET', 'POST'])
def pileup():

    # Render an empty form for GET request
    if request.method == 'GET':
        return render_template('pileup/form.html')

    # Otherwise validate the form on a POST request
    region = request.form.get('region').encode('ascii', 'ignore')
    ids = request.form.get('ids')
    sam_upload = request.files['sam']
    fasta_upload = request.files['fasta']
    SHOWINDEL = SHOWCALC = False
    FILTER = TRUNCATE = FASTA = True
    for option in request.form.getlist('options'):
        if option == 'ShowIndel': SHOWINDEL = True
        if option == 'ShowExt': TRUNCATE = False
        if option == 'ShowCalc': SHOWCALC = True
    if not region or not sam_upload:
        flash('A reqired field is missing', 'error')
        return render_template('pileup/form.html')
    if not ids: FILTER = False
    if not fasta_upload: FASTA = False
    fasta_ids = None
    if FILTER:
        try:
            fasta_ids = map(int, ids.splitlines())
            fasta_ids.sort()
        except:
            flash('Error in the FASTID(s) provided. Place one integer on each line with no extraneous lines.', 'error')
            return render_template('pileup/form.html')

    # Now load samfile
    bam = SamUpload(sam_upload, secure_filename(sam_upload.filename))

    # Later need to incorporate a loop
    samfile = bam.bamfiles[0]

    # Get reference positions list
    ref_list = []
    for col in samfile.pileup(region=region, truncate=TRUNCATE):
        if FILTER:
            if col.reference_pos in fasta_ids:
                ref_list.append(col.reference_pos)
        else:
            ref_list.append(col.reference_pos)
            if SHOWINDEL:
                maxindel = 0
                for read in col.pileups:
                    if read.indel > maxindel:
                        maxindel = read.indel
                for z in xrange(maxindel):
                    ref_list.append(col.reference_pos + 0.01 * (z + 1))

    # Use a dictionary of lists to hold the bases and reads
    rows = []
    for read in samfile.fetch(region=region):
        base_list = []
        base_list.append(read.query_name)
        for pos in ref_list:
            base_list.append(get_refbase(read, pos))
        rows.append(base_list)

    # Print results
    new_list = []
    new_list.insert(0, "")
    for num in ref_list:
        if float(num).is_integer():
            new_list.append(num)
        else:
            new_list.append("-")
    return render_template('pileup/results.html', rows=rows, sites=new_list)
