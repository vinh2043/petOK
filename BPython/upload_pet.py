from werkzeug.utils import secure_filename

def upload_pet_image():
    if 'pet_image' not in request.files:
        return 'No file part', 400
    file = request.files['pet_image']
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # Đảm bảo tên file an toàn
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))  # Lưu file
        return redirect(url_for('uploaded_file', filename=filename))
    return 'File type not allowed', 400
