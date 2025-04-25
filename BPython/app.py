from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask import send_from_directory
import os

# ====== App Setup ======
app = Flask(__name__)
app.secret_key = 'tuvavinh'

# Cấu hình SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///petcare.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cấu hình upload ảnh
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'pets')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Tạo thư mục nếu chưa có
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# ====== DB & Migrate Setup ======
db = SQLAlchemy(app)
migrate = Migrate(app, db)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/pets/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'uploads', 'pets'), filename)

# ====== Models ======
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Integer, default=2)  # 1 = admin, 2 = user

class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    image_filename = db.Column(db.String(100))  # hình ảnh thú cưng
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref=db.backref('pets', lazy=True))


# ====== Routes ======
@app.route('/')
def home():
    return redirect(url_for('login'))  # Chuyển hướng luôn đến login


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash('Mật khẩu xác nhận không khớp.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email đã tồn tại.', 'error')
            return redirect(url_for('register'))

        role = 1 if email == "admin@example.com" else 2
        new_user = User(fullname=fullname, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Đăng ký thành công. Hãy đăng nhập!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session['fullname'] = user.fullname
            session['role'] = user.role
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Sai email hoặc mật khẩu.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để tiếp tục.', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất.', 'info')
    return redirect(url_for('home'))


@app.route('/pets', methods=['GET', 'POST'])
def pets():
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        pet_type = request.form['type']
        age = int(request.form['age'])

        # Lấy file ảnh từ form
        file = request.files.get('pet_image')
        image_filename = None

        # Nếu có file và hợp lệ
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # Đảm bảo thư mục tồn tại
            upload_folder = app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)

            # Lưu ảnh vào thư mục
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            image_filename = filename

        # Tạo bản ghi Pet mới, gán tên file ảnh nếu có
        new_pet = Pet(
            name=name,
            type=pet_type,
            age=age,
            user_id=session['user_id'],
            image_filename=image_filename
        )

        db.session.add(new_pet)
        db.session.commit()
        flash('Thêm thú cưng thành công!', 'success')
        return redirect(url_for('pets'))

    pet_list = Pet.query.all()
    return render_template('pets.html', pets=pet_list, role=session.get('role', 2))


@app.route('/pets/edit/<int:pet_id>', methods=['GET', 'POST'])
def edit_pet(pet_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != 1:
        flash('Bạn không có quyền chỉnh sửa thú cưng.', 'error')
        return redirect(url_for('pets'))

    pet = Pet.query.get_or_404(pet_id)

    if request.method == 'POST':
        pet.name = request.form['name']
        pet.type = request.form['type']
        pet.age = int(request.form['age'])

        # Kiểm tra xem người dùng có chọn ảnh mới không
        if 'pet_image' in request.files:
            file = request.files['pet_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Lưu ảnh mới vào thư mục và lưu tên ảnh vào cơ sở dữ liệu
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                pet.image_filename = filename  # Cập nhật tên ảnh trong cơ sở dữ liệu

        db.session.commit()
        flash('Cập nhật thành công!', 'success')
        return redirect(url_for('pets'))

    return render_template('edit_pet.html', pet=pet)



@app.route('/pets/delete/<int:pet_id>', methods=['POST'])
def delete_pet(pet_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != 1:
        flash('Bạn không có quyền xóa thú cưng.', 'error')
        return redirect(url_for('pets'))

    pet = Pet.query.get_or_404(pet_id)
    db.session.delete(pet)
    db.session.commit()
    flash('Đã xóa thú cưng.', 'info')
    return redirect(url_for('pets'))


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('pet_image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return f'Đã tải lên ảnh: {filename}'
        return 'File không hợp lệ hoặc không chọn ảnh!'
    return render_template('upload_pet_image.html')


# ====== Chạy app ======
if __name__ == '__main__':
    app.run(debug=True)
