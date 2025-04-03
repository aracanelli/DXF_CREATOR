from flask import Flask, render_template, request, send_file
import pandas as pd
import ezdxf
import tempfile
import os
import shutil
import zipfile

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        df = pd.read_excel(file)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df.to_excel(temp.name, index=False)
        return render_template(
            "index.html",
            columns=list(df.columns),
            required_fields=["Geom_type", "center_delta_x", "center_delta_y", "Diam_width", "Height", "Part_no", "Interface_part_name"],
            file_path=temp.name
        )

    elif request.method == 'POST' and 'file_path' in request.form:
        file_path = request.form['file_path']
        mapping = {key: request.form[key] for key in request.form if key != 'file_path'}
        df = pd.read_excel(file_path)
        
        output_dir = "generated_dxf_files"
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)

        for part_no, part_group in df.groupby(mapping['Part_no']):
            for interface_name, interface_group in part_group.groupby(mapping['Interface_part_name']):
                part_dir = os.path.join(output_dir, str(part_no))
                interface_dir = os.path.join(part_dir, str(interface_name))
                os.makedirs(interface_dir, exist_ok=True)

                doc = ezdxf.new(dxfversion="R2010")
                msp = doc.modelspace()

                if interface_name not in doc.layers:
                    doc.layers.add(name=str(interface_name))

                for _, row in interface_group.iterrows():
                    shape = str(row[mapping['Geom_type']]).strip().lower()
                    x = row[mapping['center_delta_x']]
                    y = row[mapping['center_delta_y']]
                    width = row[mapping['Diam_width']]
                    height = row[mapping['Height']]
                    layer_name = str(row[mapping['Interface_part_name']])

                    if shape == 'circle':
                        msp.add_circle(center=(x, y), radius=width / 2, dxfattribs={"layer": layer_name})
                    elif shape == 'rectangle':
                        hw, hh = width / 2, height / 2
                        points = [(x - hw, y - hh), (x + hw, y - hh), (x + hw, y + hh), (x - hw, y + hh)]
                        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer_name})
                    text = msp.add_text(str(row[mapping['Part_no']]), dxfattribs={"height": 2.5, "layer": layer_name})
                    text.dxf.insert = (x, y - 5)

                dxf_filename = f"{interface_name}.dxf"
                dxf_path = os.path.join(interface_dir, dxf_filename)
                doc.saveas(dxf_path)

        zip_path = "generated_dxf_files.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)
        
        return send_file(zip_path, as_attachment=True, download_name="generated_dxf_files.zip")

    return render_template("index.html", columns=None, required_fields=None, file_path=None)

if __name__ == '__main__':
    app.run(debug=True)
