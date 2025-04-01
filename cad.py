from flask import Flask, render_template, request, send_file
import pandas as pd
import ezdxf
import tempfile
import os

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

        # Generate DXF
        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        for layer in df[mapping['Interface_part_name']].unique():
            if layer not in doc.layers:
                doc.layers.add(name=layer)

        for _, row in df.iterrows():
            shape = str(row[mapping['Geom_type']]).strip().lower()
            x = row[mapping['center_delta_x']]
            y = row[mapping['center_delta_y']]
            width = row[mapping['Diam_width']]
            height = row[mapping['Height']]
            part_no = row[mapping['Part_no']]
            layer_name = row[mapping['Interface_part_name']]

            if shape == 'circle':
                msp.add_circle(center=(x, y), radius=width / 2, dxfattribs={"layer": layer_name})
            elif shape == 'rectangle':
                hw, hh = width / 2, height / 2
                points = [(x - hw, y - hh), (x + hw, y - hh), (x + hw, y + hh), (x - hw, y + hh)]
                msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer_name})
            text = msp.add_text(part_no, dxfattribs={"height": 2.5, "layer": layer_name})
            text.dxf.insert = (x, y - 5)

        dxf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.dxf').name
        doc.saveas(dxf_path)
        return send_file(dxf_path, as_attachment=True, download_name="generated_output.dxf")

    return render_template("index.html", columns=None, required_fields=None, file_path=None)

if __name__ == '__main__':
    app.run(debug=True)
