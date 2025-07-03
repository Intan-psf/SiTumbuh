from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy import distinct
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import pickle
import csv
import os
import json
import requests
import base64
from twilio.rest import Client
from datetime import datetime, timedelta
import pymysql

pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rahasia123')
app.permanent_session_lifetime = timedelta(days=7)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/users_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'img')
db = SQLAlchemy(app)

MIDTRANS_CLIENT_KEY = "SB-Mid-client-lgO6I98U60jRgfFb"
MIDTRANS_SERVER_KEY = "SB-Mid-server-rLgSa_UWJrogo1i-zuhn-1Hw"
MIDTRANS_IS_PRODUCTION = False
MIDTRANS_MERCHANT_ID = "G218967277"

MIDTRANS_API_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"
MIDTRANS_STATUS_URL = "https://api.sandbox.midtrans.com/v2"

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='users_db',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

@app.before_request
def make_session_permanent():
    session.permanent = True

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class KegiatanPosyandu(db.Model):
    __tablename__ = 'kegiatan_posyandu'
    id = db.Column(db.Integer, primary_key=True)
    nama_posyandu = db.Column(db.String(255), nullable=False)
    tanggal_kegiatan = db.Column(db.Date, nullable=False)
    waktu_mulai = db.Column(db.Time, nullable=False)
    waktu_selesai = db.Column(db.Time, nullable=False)
    tempat_kegiatan = db.Column(db.String(255), nullable=False)
    diskripsi = db.Column(db.Text)
    foto = db.Column(db.String(255))
    kader_id = db.Column(db.Integer, db.ForeignKey('kader.id_kader'), nullable=True)

class Kader(db.Model):
    __tablename__ = 'kader'
    id_kader = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    no_telepon = db.Column(db.String(20))
    alamat = db.Column(db.Text)
    wilayah_posyandu = db.Column(db.String(100))
    tanggal_daftar = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(20), default='pending')

class PendaftaranPosyandu(db.Model):
    __tablename__ = 'pendaftaran_posyandu'
    id = db.Column(db.Integer, primary_key=True)
    kegiatan_id = db.Column(db.Integer, db.ForeignKey('kegiatan_posyandu.id'), nullable=False)
    nama_ortu = db.Column(db.String(100), nullable=False)
    nama_anak = db.Column(db.String(100), nullable=False)
    umur_anak = db.Column(db.Integer, nullable=False)
    nik = db.Column(db.String(20), nullable=False)
    alamat = db.Column(db.Text, nullable=False)
    no_hp = db.Column(db.String(20), nullable=False)
    tanggal_daftar = db.Column(db.DateTime, server_default=func.now())
    wa_terkirim = db.Column(db.Boolean, default=False)
    wa_terkirim_pada = db.Column(db.DateTime, nullable=True)
    id_anak = db.Column(db.Integer, db.ForeignKey('Anak.id'), nullable=True)
    anak_obj = db.relationship('Anak', backref=db.backref('pendaftaran_posyandu_list', lazy=True))
    kegiatan = db.relationship('KegiatanPosyandu', backref=db.backref('pendaftar', lazy=True))

    def __repr__(self):
        return f'<Pendaftaran {self.nama_anak} ke {self.kegiatan.nama_posyandu}>'

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    order_id = db.Column(db.String(255), unique=True, nullable=False)
    transaction_time = db.Column(db.DateTime, nullable=True)
    transaction_status = db.Column(db.String(50), nullable=True)
    payment_type = db.Column(db.String(50), nullable=True)
    gross_amount = db.Column(db.Integer, nullable=False)
    doctor_name = db.Column(db.String(255), nullable=False)
    doctor_id = db.Column(db.Integer, nullable=False)
    snap_token = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    appointment_date = db.Column(db.Date, nullable=True)
    appointment_time = db.Column(db.Time, nullable=True)

class CatatanPertumbuhan(db.Model):
    __tablename__ = 'CatatanPertumbuhan'
    id = db.Column(db.Integer, primary_key=True)
    id_anak = db.Column(db.Integer, db.ForeignKey('Anak.id'), nullable=False)
    tanggal_pengukuran = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    berat_kg = db.Column(db.Float, nullable=False)
    tinggi_cm = db.Column(db.Float, nullable=False)
    lingkar_kepala_cm = db.Column(db.Float, nullable=True)
    lila_cm = db.Column(db.Float, nullable=True)
    keterangan = db.Column(db.Text, nullable=True)
    anak = db.relationship('Anak', backref=db.backref('catatan_pertumbuhan_list', lazy=True))

class Dokter:
    def __init__(self, id, name, email, password_hash):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash

    @staticmethod
    def get_by_email(email):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, email, password FROM doctors WHERE email = %s", (email,))
                row = cursor.fetchone()
                if row:
                    return Dokter(row['id'], row['name'], row['email'], row['password'])
        finally:
            conn.close()
        return None

    @staticmethod
    def get_by_id(doctor_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, email, password FROM doctors WHERE id = %s", (doctor_id,))
                row = cursor.fetchone()
                if row:
                    return Dokter(row['id'], row['name'], row['email'], row['password'])
        finally:
            conn.close()
        return None


    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Anak(db.Model):
    __tablename__ = 'Anak'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nama = db.Column(db.String(255), nullable=False)
    tanggal_lahir = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    user = db.relationship('User', backref=db.backref('anak_list', lazy=True))

# Load model stunting
with open('lgbmnew.pkl', 'rb') as file:
    model_stunting = pickle.load(file)

# --- ROUTES AWAL (TIDAK BERUBAH SIGNIFIKAN) ---

@app.route('/test_db')
def test_db():
    try:
        users = User.query.all()
        return '<br>'.join([f'{u.id}: {u.name} ({u.email})' for u in users])
    except Exception as e:
        return f"Error koneksi DB: {e}"

@app.route('/')
def index():
    if 'user_id' not in session:
        flash('Silakan registrasi terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['user_id']).first()
    if not user:
        flash('User tidak ditemukan, silakan login ulang.', 'danger')
        session.pop('user_id', None)
        return redirect(url_for('login'))

    return render_template('index.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar!', 'danger')
            return render_template('logregis.html')

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Pendaftaran berhasil!', 'success')
        return redirect(url_for('login'))
    return render_template('logregis.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['user_id'] = user.id
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email atau password salah!', 'danger')
    return render_template('logregis.html')






@app.route('/logout') # Logout untuk User Biasa
def logout():
    print("DEBUG: Menghapus sesi user.")
    session.pop('user_id', None)
    session.pop('kader_id', None) # Pastikan juga menghapus kader_id jika ada
    session.clear() # Ini akan menghapus semua item dari sesi, cara paling aman
    flash('Anda berhasil logout.', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
def profile_dashboard():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['user_id']).first()
    if not user:
        flash('User tidak ditemukan, silakan login ulang.', 'danger')
        session.pop('user_id', None)
        return redirect(url_for('login'))

    anak_list = Anak.query.filter_by(user_id=user.id).all()

    anak_data_lengkap = []
    for anak in anak_list:
        catatan_terbaru = CatatanPertumbuhan.query.filter_by(id_anak=anak.id)\
                                                  .order_by(CatatanPertumbuhan.tanggal_pengukuran.desc()).first()
        anak_data_lengkap.append({
            'id': anak.id,
            'nama': anak.nama,
            'tanggal_lahir': anak.tanggal_lahir,
            'gender': anak.gender,
            'catatan_terbaru': catatan_terbaru
        })

    grafik_data_pertumbuhan = {'labels': [], 'datasets': [{'label': 'Tinggi (cm)', 'data': []}, {'label': 'Berat (kg)', 'data': []}]}
    if anak_list:
        catatan_anak_pertama = CatatanPertumbuhan.query.filter_by(id_anak=anak_list[0].id)\
                                                      .order_by(CatatanPertumbuhan.tanggal_pengukuran.asc()).all()
        for catatan in catatan_anak_pertama:
            grafik_data_pertumbuhan['labels'].append(catatan.tanggal_pengukuran.strftime('%d %b %Y'))
            grafik_data_pertumbuhan['datasets'][0]['data'].append(catatan.tinggi_cm)
            grafik_data_pertumbuhan['datasets'][1]['data'].append(catatan.berat_kg)

    return render_template('profile_dashboard.html', user=user, anak_data_lengkap=anak_data_lengkap, grafik_data_pertumbuhan=grafik_data_pertumbuhan, datetime=datetime)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['user_id']).first()
    if not user:
        flash('User tidak ditemukan, silakan login ulang.', 'danger')
        session.pop('user_id', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_name = request.form.get('name').strip()
        new_email = request.form.get('email').lower().strip()
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if not new_name or not new_email:
            flash('Nama dan email tidak boleh kosong.', 'danger')
            return redirect(url_for('edit_profile'))

        if new_email != user.email and User.query.filter_by(email=new_email).first():
            flash('Email baru sudah terdaftar oleh pengguna lain.', 'danger')
            return redirect(url_for('edit_profile'))

        if new_password:
            if not check_password_hash(user.password, current_password):
                flash('Password lama salah.', 'danger')
                return redirect(url_for('edit_profile'))
            if new_password != confirm_new_password:
                flash('Konfirmasi password baru tidak cocok.', 'danger')
                return redirect(url_for('edit_profile'))
            if len(new_password) < 6:
                flash('Password baru minimal 6 karakter.', 'danger')
                return redirect(url_for('edit_profile'))
            user.password = generate_password_hash(new_password)

        user.name = new_name
        user.email = new_email

        try:
            db.session.commit()
            flash('Profil berhasil diperbarui!', 'success')
            return redirect(url_for('profile_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal memperbarui profil: {str(e)}', 'danger')
            return redirect(url_for('edit_profile'))
    return render_template('edit_profile.html', user=user)

@app.route('/profile/tambah_anak', methods=['GET', 'POST'])
def tambah_anak():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        nama = request.form.get('nama')
        tanggal_lahir_str = request.form.get('tanggal_lahir')
        gender = request.form.get('gender')

        if not all([nama, tanggal_lahir_str, gender]):
            flash('Semua kolom harus diisi.', 'danger')
            return redirect(url_for('tambah_anak'))

        try:
            tanggal_lahir = datetime.strptime(tanggal_lahir_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Format tanggal lahir tidak valid.', 'danger')
            return redirect(url_for('tambah_anak'))

        new_anak = Anak(user_id=session['user_id'], nama=nama, tanggal_lahir=tanggal_lahir, gender=gender)
        db.session.add(new_anak)
        db.session.commit()
        flash('Data anak berhasil ditambahkan!', 'success')
        return redirect(url_for('profile_dashboard'))
    return render_template('add_child.html')

@app.route('/profile/tambah_catatan_pertumbuhan/<int:id_anak>', methods=['GET', 'POST'])
def tambah_catatan_pertumbuhan(id_anak):
    is_user = 'user_id' in session
    is_kader = 'kader_id' in session

    # Debugging: Cetak isi sesi untuk melihat apakah kader_id ada
    print(f"DEBUG: Di dalam tambah_catatan_pertumbuhan. is_user: {is_user}, is_kader: {is_kader}")
    print(f"DEBUG: session['user_id']: {session.get('user_id')}, session['kader_id']: {session.get('kader_id')}")

    if not (is_user or is_kader):
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    anak = Anak.query.get_or_404(id_anak)

    # Penambahan: Pemeriksaan akses untuk kader
    if is_kader:
        kader_id = session['kader_id']
        # Dapatkan semua ID kegiatan posyandu yang diampu oleh kader ini
        kegiatan_ids_kader = [keg.id for keg in KegiatanPosyandu.query.filter_by(kader_id=kader_id).all()]
        
        # Periksa apakah anak ini terdaftar dalam salah satu kegiatan kader
        # Ini penting agar kader hanya bisa mengelola anak yang terdaftar di posyandu yang dia ampu
        is_anak_in_kaders_activity = PendaftaranPosyandu.query.\
            filter_by(id_anak=anak.id).\
            filter(PendaftaranPosyandu.kegiatan_id.in_(kegiatan_ids_kader)).\
            first()
        
        if not is_anak_in_kaders_activity:
            flash('Anda tidak memiliki akses ke data anak ini karena tidak terdaftar di kegiatan Anda.', 'danger')
            return redirect(url_for('kader_daftar_anak')) # Alihkan kembali ke daftar anak kader
    elif is_user and anak.user_id != session['user_id']:
        flash('Anda tidak memiliki akses ke data anak ini.', 'danger')
        return redirect(url_for('profile_dashboard'))

    if request.method == 'POST':
        try:
            tanggal_pengukuran_str = request.form.get('tanggal_pengukuran')
            berat_kg = request.form.get('berat_kg')
            tinggi_cm = request.form.get('tinggi_cm')
            lingkar_kepala_cm = request.form.get('lingkar_kepala_cm')
            lila_cm = request.form.get('lila_cm')
            keterangan = request.form.get('keterangan')

            if not all([tanggal_pengukuran_str, berat_kg, tinggi_cm]):
                flash('Tanggal, berat, dan tinggi harus diisi.', 'danger')
                return redirect(url_for('tambah_catatan_pertumbuhan', id_anak=anak.id))

            tanggal_pengukuran = datetime.strptime(tanggal_pengukuran_str, '%Y-%m-%d').date()
            berat_kg = float(berat_kg)
            tinggi_cm = float(tinggi_cm)
            lingkar_kepala_cm = float(lingkar_kepala_cm) if lingkar_kepala_cm else None
            lila_cm = float(lila_cm) if lila_cm else None

            new_catatan = CatatanPertumbuhan(
                id_anak=anak.id,
                tanggal_pengukuran=tanggal_pengukuran,
                berat_kg=berat_kg,
                tinggi_cm=tinggi_cm,
                lingkar_kepala_cm=lingkar_kepala_cm,
                lila_cm=lila_cm,
                keterangan=keterangan
            )
            db.session.add(new_catatan)
            db.session.commit()
            flash('Catatan pertumbuhan berhasil ditambahkan!', 'success')

            if is_kader:
                # Jika kader, alihkan ke halaman detail anak kader
                print(f"DEBUG: Mengalihkan kader ke kader_detail_anak dengan id_anak={anak.id}")
                return redirect(url_for('kader_detail_anak', id_anak=anak.id))
            else:
                # Jika pengguna biasa, alihkan ke profil dashboard mereka
                print(f"DEBUG: Mengalihkan pengguna ke profile_dashboard")
                return redirect(url_for('profile_dashboard'))

        except (KeyError, ValueError, IntegrityError) as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat pendaftaran: {e}. Pastikan semua data sudah diisi dengan benar.', 'danger')
            # Jika terjadi error, tetap alihkan ke halaman penambahan catatan (sesuai peran)
            if is_kader:
                return redirect(url_for('tambah_catatan_pertumbuhan', id_anak=anak.id))
            else:
                return redirect(url_for('tambah_catatan_pertumbuhan', id_anak=anak.id))
    # Untuk permintaan GET
    return render_template('add_growth_record.html', child=anak, datetime=datetime, is_kader=is_kader)

@app.route('/profile/edit_catatan_pertumbuhan/<int:id_catatan>', methods=['GET', 'POST'])
def edit_catatan_pertumbuhan(id_catatan):
    is_user = 'user_id' in session
    is_kader = 'kader_id' in session

    # Debugging: Cetak isi sesi untuk melihat apakah kader_id ada
    print(f"DEBUG: Di dalam edit_catatan_pertumbuhan. is_user: {is_user}, is_kader: {is_kader}")
    print(f"DEBUG: session['user_id']: {session.get('user_id')}, session['kader_id']: {session.get('kader_id')}")

    if not (is_user or is_kader):
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    catatan = CatatanPertumbuhan.query.get_or_404(id_catatan)
    anak = catatan.anak

    if is_user and anak.user_id != session['user_id']:
        flash('Anda tidak memiliki akses untuk mengedit catatan ini.', 'danger')
        return redirect(url_for('profile_dashboard'))

    # --- PENAMBAHAN: Pemeriksaan akses untuk kader ---
    if is_kader:
        kader_id = session['kader_id']
        # Dapatkan semua ID kegiatan posyandu yang diampu oleh kader ini
        kegiatan_ids_kader = [keg.id for keg in KegiatanPosyandu.query.filter_by(kader_id=kader_id).all()]
        
        # Periksa apakah anak ini terdaftar dalam salah satu kegiatan kader
        # Ini penting agar kader hanya bisa mengedit anak yang terdaftar di posyandu yang dia ampu
        is_anak_in_kaders_activity = PendaftaranPosyandu.query.\
            filter_by(id_anak=anak.id).\
            filter(PendaftaranPosyandu.kegiatan_id.in_(kegiatan_ids_kader)).\
            first()
        
        if not is_anak_in_kaders_activity:
            flash('Anda tidak memiliki akses untuk mengedit catatan ini karena anak tidak terdaftar di kegiatan Anda.', 'danger')
            return redirect(url_for('kader_daftar_anak')) # Alihkan kembali ke daftar anak kader
    # --- AKHIR PENAMBAHAN ---

    if request.method == 'POST':
        catatan.tanggal_pengukuran = datetime.strptime(request.form.get('tanggal_pengukuran'), '%Y-%m-%d').date()
        catatan.berat_kg = float(request.form.get('berat_kg'))
        catatan.tinggi_cm = float(request.form.get('tinggi_cm'))
        catatan.lingkar_kepala_cm = float(request.form.get('lingkar_kepala_cm')) if request.form.get('lingkar_kepala_cm') else None
        catatan.lila_cm = float(request.form.get('lila_cm')) if request.form.get('lila_cm') else None
        catatan.keterangan = request.form.get('keterangan')

        db.session.commit()
        flash('Catatan pertumbuhan berhasil diperbarui!', 'success')
        if is_user:
            return redirect(url_for('profile_dashboard'))
        elif is_kader:
            return redirect(url_for('kader_detail_anak', id_anak=anak.id))
    return render_template('edit_growth_record.html', catatan=catatan, child=anak, datetime=datetime)

@app.route('/kader/daftar_anak')
def kader_daftar_anak():
    if 'kader_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    kader = Kader.query.get(session['kader_id'])
    if not kader:
        flash('Data kader tidak ditemukan.', 'danger')
        return redirect(url_for('logregmin'))

    kegiatan_kader_ids = [keg.id for keg in KegiatanPosyandu.query.filter_by(kader_id=kader.id_kader).all()]
    id_anak_yang_terdaftar_unik = db.session.query(distinct(PendaftaranPosyandu.id_anak)).\
        filter(PendaftaranPosyandu.kegiatan_id.in_(kegiatan_kader_ids)).all()
    id_anak_list = [id_anak[0] for id_anak in id_anak_yang_terdaftar_unik]
    anak_terdaftar = Anak.query.filter(Anak.id.in_(id_anak_list)).all()

    anak_data_lengkap = []
    for anak in anak_terdaftar:
        catatan_terakhir = CatatanPertumbuhan.query.filter_by(id_anak=anak.id)\
                                                .order_by(CatatanPertumbuhan.tanggal_pengukuran.desc()).first()
        anak_data_lengkap.append({
            'id': anak.id,
            'nama': anak.nama,
            'tanggal_lahir': anak.tanggal_lahir,
            'gender': anak.gender,
            'catatan_terakhir': catatan_terakhir,
            'user_nama': anak.user.name
        })
    return render_template('kader/daftar_anak.html',
                        kader=kader,
                        anak_data_lengkap=anak_data_lengkap)

@app.route('/kader/anak/<int:id_anak>')
def kader_detail_anak(id_anak):
    if 'kader_id' not in session:
        flash('Silakan login sebagai kader terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    kader = Kader.query.get(session['kader_id'])
    if not kader:
        flash('Data kader tidak ditemukan.', 'danger')
        return redirect(url_for('logregmin'))

    anak = Anak.query.get_or_404(id_anak)
    kegiatan_ids_kader = [keg.id for keg in KegiatanPosyandu.query.filter_by(kader_id=kader.id_kader).all()]
    is_anak_in_kaders_activity = PendaftaranPosyandu.query.\
        filter_by(id_anak=anak.id).\
        filter(PendaftaranPosyandu.kegiatan_id.in_(kegiatan_ids_kader)).\
        first()

    if not is_anak_in_kaders_activity:
        flash('Anda tidak memiliki akses ke data anak ini karena tidak terdaftar di kegiatan Anda.', 'danger')
        return redirect(url_for('kader_daftar_anak'))

    catatan_pertumbuhan = CatatanPertumbuhan.query.filter_by(id_anak=id_anak)\
                                                .order_by(CatatanPertumbuhan.tanggal_pengukuran.asc()).all()

    grafik_anak_data = {'labels': [], 'datasets': [
        {'label': 'Tinggi (cm)', 'data': [], 'borderColor': 'rgba(75, 192, 192, 1)', 'backgroundColor': 'rgba(75, 192, 192, 0.2)'},
        {'label': 'Berat (kg)', 'data': [], 'borderColor': 'rgba(153, 102, 255, 1)', 'backgroundColor': 'rgba(153, 102, 255, 0.2)'}
    ]}
    for catatan in catatan_pertumbuhan:
        grafik_anak_data['labels'].append(catatan.tanggal_pengukuran.strftime('%d %b %Y'))
        grafik_anak_data['datasets'][0]['data'].append(catatan.tinggi_cm)
        grafik_anak_data['datasets'][1]['data'].append(catatan.berat_kg)
    return render_template('kader/detail_anak.html',
                        anak=anak,
                        catatan_pertumbuhan=catatan_pertumbuhan,
                        grafik_anak_data=grafik_anak_data,
                        datetime=datetime,
                        kader=kader)

@app.route('/prediksi', methods=['GET', 'POST'])
def prediksi():
    if request.method == 'POST':
        try:
            nama = request.form.get('nama')
            jenis_kelamin = request.form.get('jenis_kelamin')
            umur = request.form.get('umur')
            tinggi = request.form.get('tinggi')
            berat = request.form.get('berat')

            if not (nama and umur and tinggi and berat and jenis_kelamin):
                return render_template('prediksi.html', error="Semua data harus diisi.", hasil_stunting='', risiko_stunting='')

            umur = int(umur)
            tinggi = float(tinggi)
            berat = float(berat)
            jk_encoded = 0 if jenis_kelamin.lower() == 'l' else 1

            file_path = 'data_input.csv'
            file_exists = os.path.isfile(file_path)
            with open(file_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(['Nama', 'Jenis Kelamin', 'Umur', 'Tinggi', 'Berat'])
                writer.writerow([nama, jenis_kelamin, umur, tinggi, berat])

            data_input = np.array([[jk_encoded, umur, tinggi, berat]])
            prediksi_stunting = model_stunting.predict(data_input)[0]

            if prediksi_stunting == 0:
                hasil_stunting = "Normal"
                risiko_stunting = "Rendah"
            elif prediksi_stunting == 1:
                hasil_stunting = "Risiko Tinggi"
                risiko_stunting = "Tinggi"
            elif prediksi_stunting == 2:
                hasil_stunting = "Risiko Sedang"
                risiko_stunting = "Sedang"
            else:
                hasil_stunting = "Risiko Rendah"
                risiko_stunting = "Rendah"

            return render_template('prediksi.html', hasil_stunting=hasil_stunting, risiko_stunting=risiko_stunting, error='')

        except Exception as e:
            return render_template('prediksi.html', error=f"Error: {e}", hasil_stunting='', risiko_stunting='')
    return render_template('prediksi.html', hasil_stunting='', risiko_stunting='', error='')

@app.route('/posyandu', methods=['GET', 'POST'])
def posyandu():
    if request.method == 'POST':
        nama = request.form['nama_posyandu']
        tanggal = request.form['tanggal_kegiatan']
        waktu_mulai = request.form['waktu_mulai']
        waktu_selesai = request.form['waktu_selesai']
        tempat = request.form['tempat_kegiatan']
        diskripsi = request.form['diskripsi']
        foto = request.files['foto']

        foto_filename = secure_filename(foto.filename)
        try:
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))
        except Exception as e:
            flash(f"Gagal menyimpan foto: {e}", "danger")
            return redirect(url_for('posyandu'))

        kegiatan = KegiatanPosyandu(
            nama_posyandu=nama,
            tanggal_kegiatan=tanggal,
            waktu_mulai=waktu_mulai,
            waktu_selesai=waktu_selesai,
            tempat_kegiatan=tempat,
            diskripsi=diskripsi,
            foto=foto_filename
        )
        db.session.add(kegiatan)
        db.session.commit()
        flash('Data kegiatan berhasil ditambahkan!', 'success')
        return redirect(url_for('posyandu'))

    query = request.args.get('query', '')
    if query:
        kegiatan = KegiatanPosyandu.query.filter(KegiatanPosyandu.nama_posyandu.ilike(f"%{query}%")).all()
    else:
        kegiatan = KegiatanPosyandu.query.all()
    return render_template('posyandu.html', kegiatan=kegiatan)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin/dashboard.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            flash('Login admin berhasil!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Login gagal!', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/kader_approval', methods=['GET', 'POST'])
def admin_kader_approval():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        kader_id = request.form.get('kader_id')
        action = request.form.get('action')
        kader = Kader.query.filter_by(id_kader=kader_id).first()

        if not kader:
            flash('Kader tidak ditemukan.', 'danger')
            return redirect(url_for('admin_kader_approval'))

        if action == 'approve':
            kader.status = 'aktif'
            flash(f'Kader {kader.username} disetujui.', 'success')
        elif action == 'reject':
            kader.status = 'ditolak'
            flash(f'Kader {kader.username} ditolak.', 'warning')
        else:
            flash('Aksi tidak valid.', 'danger')
        db.session.commit()
        return redirect(url_for('admin_kader_approval'))

    pending_kaders = Kader.query.filter_by(status='pending').all()
    return render_template('admin/kader_approval.html', pending_kaders=pending_kaders)

@app.route('/kader/logregmin', methods=['GET', 'POST'])
def logregmin():
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'login':
            username = request.form['username']
            password = request.form['password']

            kader = Kader.query.filter_by(username=username).first()

            if kader:
                if kader.status == 'aktif':
                    if check_password_hash(kader.password, password):
                        session['kader_id'] = kader.id_kader
                        session['kader_username'] = kader.username
                        session.pop('user_id', None)
                        flash('Login berhasil', 'success')
                        return redirect(url_for('kader_dashboard'))
                    else:
                        flash('Password salah', 'danger')
                else:
                    flash('Akun belum aktif atau sedang ditinjau admin', 'warning')
            else:
                flash('Username tidak ditemukan', 'danger')

        elif form_type == 'register':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            nama_lengkap = request.form['nama_lengkap']
            no_telepon = request.form.get('no_telepon')
            alamat = request.form.get('alamat')
            wilayah_posyandu = request.form.get('wilayah_posyandu')

            existing_user = Kader.query.filter(
                (Kader.username == username) | (Kader.email == email)
            ).first()

            if existing_user:
                flash('Username atau email sudah terdaftar', 'danger')
            else:
                hashed_password = generate_password_hash(password)
                new_kader = Kader(
                    username=username,
                    email=email,
                    password=hashed_password,
                    nama_lengkap=nama_lengkap,
                    no_telepon=no_telepon,
                    alamat=alamat,
                    wilayah_posyandu=wilayah_posyandu,
                    status='pending'
                )
                db.session.add(new_kader)
                db.session.commit()
                flash('Registrasi berhasil, tunggu approval admin', 'success')
                return redirect(url_for('logregmin'))
    return render_template('kader/logregmin.html')

@app.route('/admin/posyandu', methods=['GET', 'POST'])
def admin_posyandu():
    if 'kader_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    if request.method == 'POST':
        nama_posyandu = request.form['nama_posyandu']
        tanggal_kegiatan = datetime.strptime(request.form['tanggal_kegiatan'], '%Y-%m-%d').date()
        waktu_mulai = datetime.strptime(request.form['waktu_mulai'], '%H:%M').time()
        waktu_selesai = datetime.strptime(request.form['waktu_selesai'], '%H:%M').time()
        tempat_kegiatan = request.form['tempat_kegiatan']
        diskripsi = request.form.get('diskripsi')
        foto = request.files.get('foto')

        filename = None
        if foto and foto.filename != '':
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        kegiatan = KegiatanPosyandu(
            nama_posyandu=nama_posyandu,
            tanggal_kegiatan=tanggal_kegiatan,
            waktu_mulai=waktu_mulai,
            waktu_selesai=waktu_selesai,
            tempat_kegiatan=tempat_kegiatan,
            diskripsi=diskripsi,
            foto=filename,
            kader_id=session['kader_id']
        )
        db.session.add(kegiatan)
        db.session.commit()
        flash('Kegiatan berhasil ditambahkan!', 'success')
        return redirect(url_for('admin_posyandu'))

    print("Kader ID di session:", session.get('kader_id'))
    kegiatan_list = KegiatanPosyandu.query.filter_by(kader_id=session['kader_id']).all()
    return render_template('kader/tambah_posyandu.html', kegiatan_list=kegiatan_list)

@app.route('/kader/dashboard')
def kader_dashboard():
    if 'kader_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    kader = Kader.query.get(session['kader_id'])
    if not kader:
        flash('Data kader tidak ditemukan.', 'danger')
        return redirect(url_for('logregmin'))

    user_aktif = User.query.count()
    jumlah_kegiatan = KegiatanPosyandu.query.filter_by(kader_id=kader.id_kader).count()
    jumlah_pendaftaran = db.session.query(PendaftaranPosyandu)\
        .join(KegiatanPosyandu, PendaftaranPosyandu.kegiatan_id == KegiatanPosyandu.id)\
        .filter(KegiatanPosyandu.kader_id == kader.id_kader).count()

    bulan_list = ["Jan", "Feb", "Mar", "Apr"]
    data_kegiatan = [5, 8, 4, 3]

    return render_template('kader/dashboard.html',
                        kader=kader,
                        jumlah_kegiatan=jumlah_kegiatan,
                        jumlah_pendaftaran=jumlah_pendaftaran,
                        user_aktif=user_aktif,
                        bulan_list=bulan_list,
                        data_kegiatan=data_kegiatan)

@app.route('/kader/posyandu/edit/<int:id>', methods=['GET', 'POST'])
def edit_posyandu(id):
    if 'kader_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    kegiatan = KegiatanPosyandu.query.get_or_404(id)
    if request.method == 'POST':
        kegiatan.nama_posyandu = request.form['nama_posyandu']
        tanggal_kegiatan = datetime.strptime(request.form['tanggal_kegiatan'], '%Y-%m-%d').date()
        kegiatan.waktu_mulai = datetime.strptime(request.form['waktu_mulai'], '%H:%M').time()
        kegiatan.waktu_selesai = datetime.strptime(request.form['waktu_selesai'], '%H:%M').time()
        kegiatan.tempat_kegiatan = request.form['tempat_kegiatan']
        diskripsi = request.form['diskripsi']

        foto_file = request.files.get('foto')
        if foto_file and foto_file.filename != '':
            foto_filename = foto_file.filename
            foto_file.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))
            kegiatan.foto = foto_filename
        db.session.commit()
        flash('Data kegiatan berhasil diperbarui.', 'success')
        return redirect(url_for('admin_posyandu'))
    return render_template('kader/edit_posyandu.html', kegiatan=kegiatan)

@app.route('/admin/posyandu/delete/<int:id>')
def delete_posyandu(id):
    if 'kader_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    kegiatan = KegiatanPosyandu.query.get_or_404(id)
    PendaftaranPosyandu.query.filter_by(kegiatan_id=kegiatan.id).delete()
    db.session.delete(kegiatan)
    db.session.commit()
    flash('Kegiatan berhasil dihapus!', 'success')
    return redirect(url_for('admin_posyandu'))

@app.route('/kader/logout') # Logout untuk Kader
def kader_logout():
    print("DEBUG: Menghapus sesi kader.")
    session.pop('kader_id', None)
    session.pop('user_id', None) # Pastikan juga menghapus user_id jika ada
    session.clear() # Ini akan menghapus semua item dari sesi, cara paling aman
    flash('Berhasil logout', 'info')
    return redirect(url_for('logregmin'))

@app.route('/daftar_posyandu/<int:kegiatan_id>', methods=['GET', 'POST'])
def daftar_posyandu_form(kegiatan_id):
    kegiatan = KegiatanPosyandu.query.get_or_404(kegiatan_id)

    if 'user_id' not in session:
        flash('Anda harus login untuk mendaftar posyandu.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    anak_user_list = Anak.query.filter_by(user_id=user_id).all()

    if request.method == 'POST':
        try:
            nama_ortu = request.form['nama_ortu'].strip()
            nik = request.form['nik'].strip()
            alamat = request.form['alamat'].strip()
            no_hp = request.form['no_hp'].strip()
            anak_yang_dipilih_id = request.form.get('id_anak_pendaftaran')

            anak_yang_dipilih = Anak.query.get(anak_yang_dipilih_id)

            if not anak_yang_dipilih or anak_yang_dipilih.user_id != user_id:
                flash('Pilihan anak tidak valid atau anak tidak terdaftar di akun Anda.', 'danger')
                return redirect(request.url)

            today = datetime.now().date()
            umur_dalam_bulan = (today.year - anak_yang_dipilih.tanggal_lahir.year) * 12 + (today.month - anak_yang_dipilih.tanggal_lahir.month)

            pendaftaran = PendaftaranPosyandu(
                kegiatan_id=kegiatan_id,
                nama_ortu=nama_ortu,
                nama_anak=anak_yang_dipilih.nama,
                umur_anak=umur_dalam_bulan,
                nik=nik,
                alamat=alamat,
                no_hp=no_hp,
                id_anak=anak_yang_dipilih.id
            )
            db.session.add(pendaftaran)
            db.session.commit()

            flash('Pendaftaran berhasil! Terima kasih telah mendaftar.', 'success')
            return redirect(url_for('posyandu'))

        except (KeyError, ValueError, IntegrityError) as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat pendaftaran: {e}. Pastikan semua data sudah diisi dengan benar.', 'danger')
            return redirect(request.url)
    return render_template('daftar_posyandu.html', kegiatan=kegiatan, anak_user_list=anak_user_list)

@app.route('/kader/tambah_posyandu', methods=['GET', 'POST'])
def admin_tambahpos():
    if 'kader_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    kegiatan_list = KegiatanPosyandu.query.filter_by(kader_id=session['kader_id']).all()

    if request.method == 'POST':
        try:
            nama_posyandu = request.form['nama_posyandu']
            tanggal_kegiatan = datetime.strptime(request.form['tanggal_kegiatan'], '%Y-%m-%d').date()
            waktu_mulai = datetime.strptime(request.form['waktu_mulai'], '%H:%M').time()
            waktu_selesai = datetime.strptime(request.form['waktu_selesai'], '%H:%M').time()
            tempat_kegiatan = request.form['tempat_kegiatan']
            diskripsi = request.form.get('diskripsi')

            foto_file = request.files.get('foto')
            foto_filename = None
            if foto_file and foto_file.filename != '':
                foto_filename = secure_filename(foto_file.filename)
                foto_file.save(f'static/uploads/{foto_filename}')

            kegiatan_baru = KegiatanPosyandu(
                nama_posyandu=nama_posyandu,
                tanggal_kegiatan=tanggal_kegiatan,
                waktu_mulai=waktu_mulai,
                waktu_selesai=waktu_selesai,
                tempat_kegiatan=tempat_kegiatan,
                diskripsi=diskripsi,
                foto=foto_filename,
                kader_id=session['kader_id']
            )
            db.session.add(kegiatan_baru)
            db.session.commit()
            flash('Kegiatan Posyandu berhasil ditambahkan!', 'success')
            return redirect(url_for('admin_tambahpos'))

        except Exception as e:
            flash(f'Gagal menambahkan kegiatan: {str(e)}', 'danger')
            return redirect(url_for('admin_tambahpos'))
    return render_template('kader/tambah_posyandu.html', kegiatan_list=kegiatan_list)

@app.route('/kader/daftar_posyandu')
def admin_dafpos():
    if 'kader_id' not in session and not session.get('admin_logged_in'):
        flash('Silakan login sebagai kader atau admin terlebih dahulu.', 'warning')
        return redirect(url_for('logregmin'))

    daftar_pendaftaran = []
    if 'kader_id' in session:
        kader = Kader.query.get(session.get('kader_id'))
        if kader:
            daftar_pendaftaran = db.session.query(PendaftaranPosyandu)\
                .join(KegiatanPosyandu, PendaftaranPosyandu.kegiatan_id == KegiatanPosyandu.id)\
                .filter(KegiatanPosyandu.kader_id == session['kader_id'])\
                .all()
    elif session.get('admin_logged_in'):
        daftar_pendaftaran = PendaftaranPosyandu.query.all()

    kegiatan_list = KegiatanPosyandu.query.all()
    return render_template('kader/dafpos.html', kegiatan_list=kegiatan_list, daftar_pendaftaran=daftar_pendaftaran)

@app.route('/kader/kirim_wa/<int:pendaftaran_id>')
def kirim_wa(pendaftaran_id):
    pendaftar = PendaftaranPosyandu.query.get_or_404(pendaftaran_id)
    print(f"[DEBUG] Sebelum update: {pendaftar.wa_terkirim}, {pendaftar.wa_terkirim_pada}")

    # Log nomor HP sebelum dan sesudah format
    no_hp_raw = pendaftar.no_hp
    print(f"[DEBUG] Nomor HP dari database (raw): {no_hp_raw}")

    no_hp_formatted = no_hp_raw
    if no_hp_formatted.startswith("0"):
        no_hp_formatted = "+62" + no_hp_formatted[1:]
    elif not no_hp_formatted.startswith("+"): # Jika tidak diawali 0 atau +, asumsikan 62
        no_hp_formatted = "+62" + no_hp_formatted
    print(f"[DEBUG] Nomor HP setelah format internasional: {no_hp_formatted}")

    jadwal_str = pendaftar.kegiatan.tanggal_kegiatan.strftime('%d-%m-%Y') + " pukul " + pendaftar.kegiatan.waktu_mulai.strftime('%H:%M') + " WIB"

    # --- KREDENSIAL TWILIO ANDA ---
    # Gunakan kredensial yang Anda berikan
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    # Pastikan nomor Twilio WhatsApp ini adalah nomor pengirim Anda (sandbox atau nomor aktif)
    # Biasanya dimulai dengan whatsapp:+1234567890 (untuk sandbox) atau whatsapp:+62.... (untuk nomor Indonesia)
    twilio_whatsapp_number = 'whatsapp:+14155238886' # Ini nomor sandbox default. Pastikan Anda sudah mengaktifkannya

    client = Client(account_sid, auth_token)

    try:
        print(f"[DEBUG] Mengirim pesan WA dari '{twilio_whatsapp_number}' ke '{no_hp_formatted}'")
        message = client.messages.create(
            from_=twilio_whatsapp_number,
            body=f"Halo {pendaftar.nama_ortu}, jadwal posyandu Anda adalah tanggal {jadwal_str}. Sampai jumpa!",
            to=f'whatsapp:{no_hp_formatted}'
        )
        pendaftar.wa_terkirim = True
        pendaftar.wa_terkirim_pada = datetime.utcnow()
        db.session.add(pendaftar)
        db.session.commit()

        print(f"[DEBUG] Setelah update: {pendaftar.wa_terkirim}, {pendaftar.wa_terkirim_pada}")
        print(f"[DEBUG] Pesan berhasil dikirim. Message SID: {message.sid}") # Menampilkan SID pesan Twilio
        flash('Pesan WhatsApp berhasil dikirim!', 'success')
    except Exception as e:
        # Menangkap error lebih spesifik
        print(f"[DEBUG] Terjadi error saat kirim WA: {e}")
        print(f"[DEBUG] Tipe Error: {type(e).__name__}")
        flash(f'Gagal mengirim pesan: {e}. Pastikan nomor WA tujuan benar dan akun Twilio aktif.', 'danger')
    return redirect(url_for('admin_dafpos'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_username', None)
    flash('Berhasil logout admin', 'info')
    return redirect(url_for('admin_login'))

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/kontak-kami')
def kontakkami():
    return render_template('kontakkami.html')

@app.route('/doctor')
def doctor():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['user_id']).first()
    if not user:
        flash('User tidak ditemukan, silakan login ulang.', 'danger')
        session.pop('user_id', None)
        return redirect(url_for('login'))
    return render_template('doctor.html', user=user, midtrans_client_key=MIDTRANS_CLIENT_KEY)

@app.route('/payment_history')
def payment_history():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    payments = Payment.query.filter_by(user_id=session['user_id']).order_by(Payment.created_at.desc()).all()
    return render_template('payment_history.html', payments=payments, midtrans_client_key=MIDTRANS_CLIENT_KEY)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    try:
        data = request.get_json()
        required_fields = ['doctorId', 'doctorName', 'fee', 'firstName', 'lastName',
                        'email', 'phone', 'date', 'time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f"Missing required field: {field}"
                }), 400

        order_id = f"DOCTOR-{session['user_id']}-{int(datetime.now().timestamp())}"
        try:
            amount = int(data['fee'].replace('Rp ', '').replace('.', '').strip())
        except ValueError:
            app.logger.warning(f"Failed to parse fee amount: {data['fee']}, defaulting to 50000")
            amount = 50000

        transaction_data = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": amount
            },
            "customer_details": {
                "first_name": data['firstName'],
                "last_name": data['lastName'],
                "email": data['email'],
                "phone": data['phone']
            },
            "item_details": [{
                "id": f"DOCTOR-{data['doctorId']}",
                "price": amount,
                "quantity": 1,
                "name": f"Appointment with {data['doctorName']}"
            }],
            "callbacks": {
                "finish": url_for('payment_status', _external=True),
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SiTumbuh/1.0",
            "Authorization": "Basic " + base64.b64encode((MIDTRANS_SERVER_KEY + ":").encode()).decode()
        }

        try:
            app.logger.info(f"Sending request to Midtrans API: {MIDTRANS_API_URL}")
            app.logger.info(f"Request payload: {json.dumps(transaction_data)}")

            response = requests.post(
                MIDTRANS_API_URL,
                headers=headers,
                data=json.dumps(transaction_data),
                timeout=30
            )

            app.logger.info(f"Midtrans response status: {response.status_code}")
            app.logger.info(f"Midtrans response headers: {response.headers}")
            app.logger.info(f"Midtrans response text: {response.text[:500]}")

            try:
                response_data = response.json()
                app.logger.info(f"Parsed JSON response: {response_data}")
            except ValueError:
                app.logger.error(f"Non-JSON response from Midtrans: {response.text}")
                return jsonify({
                    'success': False,
                    'message': 'Invalid response from payment gateway'
                }), 500

            if response.status_code == 201:
                try:
                    appointment_date = datetime.strptime(data['date'], '%Y-%m-%d').date() if data['date'] else None
                    appointment_time = datetime.strptime(data['time'], '%H:%M').time() if data['time'] else None

                    payment = Payment(
                        user_id=session['user_id'],
                        order_id=order_id,
                        transaction_status='pending',
                        gross_amount=amount,
                        doctor_name=data['doctorName'],
                        doctor_id=data['doctorId'],
                        snap_token=response_data['token'],
                        appointment_date=appointment_date,
                        appointment_time=appointment_time
                    )
                    db.session.add(payment)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Database error: {e}")
                    app.logger.warning("Continuing with payment despite database error")
                return jsonify({
                    'success': True,
                    'snap_token': response_data['token'],
                    'order_id': order_id
                })
            else:
                app.logger.error(f"Midtrans error: {response_data}")
                error_message = response_data.get('error_messages', ['Unknown error'])[0] if 'error_messages' in response_data else 'Failed to create transaction'
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            app.logger.error(f"Request error: {error_msg}")
            if isinstance(e, requests.exceptions.Timeout):
                message = 'Koneksi ke Midtrans timeout. Silakan coba lagi.'
            elif isinstance(e, requests.exceptions.ConnectionError):
                message = 'Tidak dapat terhubung ke Midtrans. Periksa koneksi internet Anda.'
            else:
                message = 'Gagal terhubung ke layanan pembayaran. Silakan coba lagi.'
            return jsonify({
                'success': False,
                'message': message,
                'error_details': error_msg
            }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred'
        }), 500

@app.route('/payment_status')
def payment_status():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    order_id = request.args.get('order_id')
    transaction_status = request.args.get('transaction_status')

    if order_id and transaction_status:
        payment = Payment.query.filter_by(order_id=order_id).first()
        if payment:
            payment.transaction_status = transaction_status
            payment.transaction_time = datetime.now()
            db.session.commit()
    return render_template('payment_status.html', midtrans_client_key=MIDTRANS_CLIENT_KEY)

@app.route('/api/verify-doctor-implementation')
def verify_doctor_implementation():
    try:
        payment_table_exists = Payment.__table__.exists(db.engine)
        doctor_images = []
        for i in range(1, 7):
            image_path = os.path.join('static', 'img', f'doktor{i}.png')
            if os.path.exists(image_path):
                doctor_images.append(f'doktor{i}.png')

        doctor_js_path = os.path.join('static', 'js', 'doctor.js')
        doctor_js_exists = os.path.exists(doctor_js_path)
        doctor_css_path = os.path.join('static', 'css', 'doctor.css')
        doctor_css_exists = os.path.exists(doctor_css_path)
        doctor_template_exists = os.path.exists(os.path.join('templates', 'doctor.html'))
        payment_status_exists = os.path.exists(os.path.join('templates', 'payment_status.html'))
        payment_history_exists = os.path.exists(os.path.join('templates', 'payment_history.html'))

        return jsonify({
            'success': True,
            'payment_table_exists': payment_table_exists,
            'doctor_images': doctor_images,
            'doctor_js_exists': doctor_js_exists,
            'doctor_css_exists': doctor_css_exists,
            'templates': {
                'doctor_html': doctor_template_exists,
                'payment_status_html': payment_status_exists,
                'payment_history_html': payment_history_exists
            },
            'midtrans_keys': {
                'client_key': MIDTRANS_CLIENT_KEY[:10] + '...',
                'is_production': MIDTRANS_IS_PRODUCTION
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/check_payment_status', methods=['POST'])
def check_payment_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'success': False, 'message': 'No order ID provided'}), 400

    try:
        payment = Payment.query.filter_by(order_id=order_id).first()

        if not payment:
            if 'transaction_status' in data:
                return jsonify({
                    'success': True,
                    'transaction_status': data.get('transaction_status', 'error'),
                    'payment_type': data.get('payment_type', 'Unknown'),
                    'gross_amount': data.get('gross_amount', 0),
                    'transaction_time': datetime.now().isoformat()
                })
            else:
                app.logger.error(f"Payment not found for order_id: {order_id}")
                return jsonify({
                    'success': False,
                    'message': 'Payment not found',
                    'transaction_status': 'error',
                    'payment_type': 'Unknown',
                    'gross_amount': 0,
                    'transaction_time': datetime.now().isoformat()
                })

        doctor_info = {
            'id': payment.doctor_id,
            'name': payment.doctor_name
        }
        return jsonify({
            'success': True,
            'order_id': payment.order_id,
            'transaction_status': payment.transaction_status,
            'payment_type': payment.payment_type or 'Unknown',
            'gross_amount': payment.gross_amount,
            'transaction_time': payment.transaction_time.isoformat() if payment.transaction_time else datetime.now().isoformat(),
            'doctor': doctor_info,
            'appointment_date': payment.appointment_date.isoformat() if payment.appointment_date else None,
            'appointment_time': payment.appointment_time.isoformat() if payment.appointment_time else None
        })
    except Exception as e:
        app.logger.error(f"Error checking payment status: {e}")
        return jsonify({
            'success': False,
            'message': 'Error checking payment status',
            'transaction_status': 'error',
            'payment_type': 'Unknown',
            'gross_amount': 0,
            'transaction_time': datetime.now().isoformat()
        })

    if order_id and transaction_status:
        payment = Payment.query.filter_by(order_id=order_id).first()
        if payment:
            payment.transaction_status = transaction_status
            payment.transaction_time = datetime.now()
            db.session.commit()
    return render_template('payment_status.html', midtrans_client_key=MIDTRANS_CLIENT_KEY)

@app.route('/payment_detail')
def payment_detail():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    order_id = request.args.get('order_id')
    if not order_id:
        flash('ID Pesanan tidak valid', 'danger')
        return redirect(url_for('payment_history'))

    payment = Payment.query.filter_by(order_id=order_id, user_id=session['user_id']).first()
    if not payment:
        flash('Pembayaran tidak ditemukan', 'danger')
        return redirect(url_for('payment_history'))

    if payment.appointment_date:
        payment.appointment_date = payment.appointment_date.strftime('%d %B %Y')
    if payment.appointment_time:
        payment.appointment_time = payment.appointment_time.strftime('%H:%M')
    if payment.transaction_time:
        payment.transaction_time = payment.transaction_time.strftime('%d %B %Y %H:%M')
    return render_template('payment_detail.html', payment=payment, midtrans_client_key=MIDTRANS_CLIENT_KEY)

@app.template_filter('format_number')
def format_number(value):
    try:
        if value is None:
            return '0'
        return '{:,.0f}'.format(float(value)).replace(',', '.')
    except (ValueError, TypeError):
        return '0'

# --- CHAT ROUTES MODIFIED FOR USER AND DOCTOR ---

@app.route('/chat_dokter')
def chat_dokter():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT id, transaction_time, order_id, doctor_name, gross_amount, transaction_status FROM payments WHERE transaction_status = 'success' AND user_id = %s", (session.get('user_id'),)) # Add id and filter by user_id
    payments = cur.fetchall()
    conn.close()
    return render_template('chat_dokter.html', payments=payments)

@app.route('/chat_page/<int:pembayaran_id>', methods=['GET', 'POST'])
def chat_page(pembayaran_id):
    user_id = session.get('user_id')
    
    if not user_id:
        flash('Harap login terlebih dahulu.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    payment_info = None # Inisialisasi
    messages_raw = [] # Inisialisasi
    display_name = "Dokter Tidak Dikenal" # Inisialisasi
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, doctor_id, doctor_name FROM payments
                WHERE id = %s AND transaction_status = 'success' AND user_id = %s
            """, (pembayaran_id, user_id))
            payment_info = cursor.fetchone()

            if not payment_info:
                flash('Pembayaran tidak ditemukan atau tidak sukses untuk Anda.', 'warning')
                return redirect(url_for('chat_dokter'))

            display_name = payment_info['doctor_name']

            cursor.execute("SELECT COUNT(*) AS total FROM chat WHERE pembayaran_id = %s", (pembayaran_id,))
            total_chat = cursor.fetchone()['total']

            if total_chat == 0:
                cursor.execute("""
                    INSERT INTO chat (pembayaran_id, pengirim, pesan, waktu)
                    VALUES (%s, %s, %s, NOW())
                """, (pembayaran_id, 'doctor', f"Halo, saya dokter {payment_info['doctor_name']}. Senang bertemu Anda! Silakan berkonsultasi."))
                conn.commit()

            if request.method == 'POST':
                pesan = request.form.get('message')
                if pesan:
                    cursor.execute("""
                        INSERT INTO chat (pembayaran_id, pengirim, pesan, waktu)
                        VALUES (%s, %s, %s, NOW())
                    """, (pembayaran_id, 'user', pesan))
                    conn.commit()
                    return redirect(url_for('chat_page', pembayaran_id=pembayaran_id))

            cursor.execute("""
                SELECT pengirim, pesan, waktu FROM chat
                WHERE pembayaran_id = %s
                ORDER BY waktu ASC
            """, (pembayaran_id,))
            messages_raw = cursor.fetchall()

    finally:
        if conn:
            conn.close()

    messages = []
    for msg in messages_raw:
        waktu = msg['waktu']
        if isinstance(waktu, str):
            try:
                waktu = datetime.strptime(waktu, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                waktu = None
        waktu_formatted = waktu.strftime('%d %b %Y %H:%M:%S') if waktu else ''
        messages.append((msg['pengirim'], msg['pesan'], waktu_formatted))

    return render_template('chat_page.html',
                           doctor_name=display_name,
                           messages=messages,
                           pembayaran_id=pembayaran_id)

@app.route('/chat_api/<int:pembayaran_id>', methods=['GET'])
def chat_api(pembayaran_id):
    user_id = session.get('user_id')
    doctor_id = session.get('doctor_id')
    is_doctor = doctor_id is not None

    if not user_id and not doctor_id:
        return jsonify([])

    conn = get_db_connection()
    messages = []

    try:
        with conn.cursor() as cursor:
            # Cek apakah pembayaran valid
            cursor.execute("""
                SELECT user_id, doctor_id FROM payments
                WHERE id = %s AND transaction_status = 'success'
            """, (pembayaran_id,))
            payment_info = cursor.fetchone()

            if not payment_info:
                return jsonify([])

            # Pastikan hanya user atau dokter yang berhak bisa akses
            if is_doctor and payment_info['doctor_id'] != doctor_id:
                return jsonify([])
            if not is_doctor and payment_info['user_id'] != user_id:
                return jsonify([])

            # Ambil pesan chat
            cursor.execute("""
                SELECT pengirim, pesan, waktu FROM chat
                WHERE pembayaran_id = %s
                ORDER BY waktu ASC
            """, (pembayaran_id,))
            messages_raw = cursor.fetchall()

            # Format pesan
            for msg in messages_raw:
                waktu = msg['waktu']
                if isinstance(waktu, str):
                    try:
                        waktu = datetime.strptime(waktu, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        waktu = None
                waktu_formatted = waktu.strftime('%d %b %Y %H:%M:%S') if waktu else ''
                messages.append({
                    'pengirim': msg['pengirim'],
                    'pesan': msg['pesan'],
                    'waktu': waktu_formatted
                })

    finally:
        conn.close()

    return jsonify(messages)


# --- NEW DOCTOR CHAT RELATED ROUTES ---

@app.route('/dokter/login', methods=['GET', 'POST'])
def dokter_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        dokter = Dokter.get_by_email(email)
        if dokter and check_password_hash(dokter.password_hash, password):
            session['doctor_id'] = dokter.id
            session['doctor_name'] = dokter.name # Store doctor's name in session
            flash('Login berhasil!', 'success')
            return redirect(url_for('dokter_dashboard'))
        else:
            flash('Email atau password salah', 'danger')
    return render_template('dokter/login.html')

@app.route('/dokter/dashboard')
def dokter_dashboard():
    if 'doctor_id' not in session:
        flash('Silakan login dulu', 'warning')
        return redirect(url_for('dokter_login'))

    doctor_id = session['doctor_id']
    doctor = Dokter.get_by_id(doctor_id) # Pastikan Anda punya method get_by_id di class Dokter
    if not doctor:
        flash('Data dokter tidak ditemukan.', 'danger')
        session.pop('doctor_id', None)
        return redirect(url_for('dokter_login'))

    # Get total patients for this doctor
    total_patients_query = db.session.query(func.count(distinct(Payment.user_id))).\
        filter(Payment.doctor_id == doctor_id, Payment.transaction_status == 'success').scalar()

    today = datetime.now().date()
    consultations_today_query = Payment.query.\
        filter(Payment.doctor_id == doctor_id, 
               Payment.transaction_status == 'success',
               Payment.appointment_date == today).count()

    # Get pending responses (example, needs chat table for this logic)
    # This part requires more complex logic to determine "pending responses"
    # For now, let's just use a dummy value or count active payments that haven't been responded to recently.
    # For a real system, you'd need a last_message_from_doctor field or similar.
    pending_responses_query = Payment.query.\
        filter(Payment.doctor_id == doctor_id, 
               Payment.transaction_status == 'success').count() # Dummy count for now

    return render_template('dokter/dashboard.html',
                        doctor_name=doctor.name,
                        total_patients=total_patients_query,
                        consultations_today=consultations_today_query,
                        pending_responses=pending_responses_query)

@app.route('/dokter/chat_list')
def dokter_chat_list():
    if 'doctor_id' not in session:
        flash('Silakan login dulu', 'warning')
        return redirect(url_for('dokter_login'))

    doctor_id = session['doctor_id']
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Dapatkan semua pembayaran sukses yang terkait dengan dokter ini
            cursor.execute("""
                SELECT p.id as pembayaran_id, p.user_id, u.name as user_name,
                       p.transaction_time, p.doctor_name
                FROM payments p
                JOIN users u ON p.user_id = u.id
                WHERE p.doctor_id = %s AND p.transaction_status = 'success'
                ORDER BY p.created_at DESC
            """, (doctor_id,))
            payments_raw = cursor.fetchall()

            chat_sessions = []
            for payment in payments_raw:
                # Dapatkan pesan terakhir untuk setiap sesi chat
                cursor.execute("""
                    SELECT pengirim, pesan, waktu FROM chat
                    WHERE pembayaran_id = %s
                    ORDER BY waktu DESC LIMIT 1
                """, (payment['pembayaran_id'],))
                last_message = cursor.fetchone()

                chat_sessions.append({
                    'pembayaran_id': payment['pembayaran_id'],
                    'user_name': payment['user_name'],
                    'transaction_time': payment['transaction_time'].strftime('%d %b %Y %H:%M') if payment['transaction_time'] else 'N/A',
                    'last_message': last_message['pesan'] if last_message else 'Belum ada pesan',
                    'last_message_time': last_message['waktu'].strftime('%H:%M') if last_message and last_message['waktu'] else 'N/A'
                })
    finally:
        conn.close()

    return render_template('dokter/chat_list.html', chat_sessions=chat_sessions)


@app.route('/dokter/chat_room/<int:pembayaran_id>', methods=['GET', 'POST'])
def dokter_chat_room(pembayaran_id):
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        flash('Harap login terlebih dahulu sebagai dokter.', 'warning')
        return redirect(url_for('dokter_login'))

    conn = get_db_connection()
    payment_info = None # Inisialisasi
    messages_raw = [] # Inisialisasi
    patient_name_display = "Pasien Tidak Dikenal" # Inisialisasi

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, doctor_id, doctor_name FROM payments
                WHERE id = %s AND transaction_status = 'success' AND doctor_id = %s
            """, (pembayaran_id, doctor_id))
            payment_info = cursor.fetchone()

            if not payment_info:
                flash('Pembayaran tidak ditemukan atau tidak sukses untuk dokter ini.', 'warning')
                return redirect(url_for('dokter_chat_list'))

            patient_user = User.query.filter_by(id=payment_info['user_id']).first()
            patient_name_display = patient_user.name if patient_user else "Pasien Tidak Dikenal"

            # Pesan awal tidak perlu ditambahkan lagi karena sudah ada di rute chat_page user

            if request.method == 'POST':
                pesan = request.form.get('message')
                if pesan:
                    cursor.execute("""
                        INSERT INTO chat (pembayaran_id, pengirim, pesan, waktu)
                        VALUES (%s, %s, %s, NOW())
                    """, (pembayaran_id, 'doctor', pesan))
                    conn.commit()
                    return redirect(url_for('dokter_chat_room', pembayaran_id=pembayaran_id))

            cursor.execute("""
                SELECT pengirim, pesan, waktu FROM chat
                WHERE pembayaran_id = %s
                ORDER BY waktu ASC
            """, (pembayaran_id,))
            messages_raw = cursor.fetchall()

    finally:
        if conn:
            conn.close()

    messages = []
    for msg in messages_raw:
        waktu = msg['waktu']
        if isinstance(waktu, str):
            try:
                waktu = datetime.strptime(waktu, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                waktu = None
        waktu_formatted = waktu.strftime('%d %b %Y %H:%M:%S') if waktu else ''
        messages.append((msg['pengirim'], msg['pesan'], waktu_formatted))

    return render_template('dokter/dokter_chat_room.html',
                           patient_name=patient_name_display,
                           messages=messages,
                           pembayaran_id=pembayaran_id)

@app.route('/dokter/logout')
def dokter_logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    flash('Anda berhasil logout dokter.', 'success')
    return redirect(url_for('dokter_login'))


@app.route('/notification_handler', methods=['POST'])
def notification_handler():
    try:
        notification_data = request.get_json()
        app.logger.info(f"Received payment notification: {notification_data}")

        order_id = notification_data.get('order_id')
        transaction_status = notification_data.get('transaction_status')
        payment_type = notification_data.get('payment_type')
        transaction_time = notification_data.get('transaction_time')

        if not order_id or not transaction_status:
            app.logger.error("Invalid notification data received")
            return "Invalid notification data", 400

        payment = Payment.query.filter_by(order_id=order_id).first()

        if not payment:
            app.logger.warning(f"Payment record not found for order ID: {order_id}")
            return "OK, payment not found", 200

        payment.transaction_status = transaction_status
        payment.payment_type = payment_type

        if transaction_time:
            try:
                payment.transaction_time = datetime.strptime(transaction_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    payment.transaction_time = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
                except ValueError:
                    app.logger.warning(f"Could not parse transaction time: {transaction_time}")
                    payment.transaction_time = datetime.now()
        else:
            payment.transaction_time = datetime.now()

        db.session.commit()
        app.logger.info(f"Payment updated successfully: {order_id} -> {transaction_status}")
        return "OK", 200

    except Exception as e:
        app.logger.error(f"Error processing notification: {str(e)}")
        return "OK, error logged", 200

if __name__ == '__main__':
    app.run(debug=True)