import streamlit as st
import sqlite3
import pandas as pd
from collections import defaultdict

# Menghubungkan ke database SQLite
conn = sqlite3.connect('halal_db.db')

# Tabel untuk foodproduct
cursor_foodproduct = conn.cursor()

# Tabel untuk brand
cursor_brand = conn.cursor()

# Tabel untuk certificate
cursor_certificate = conn.cursor()

# Tabel untuk manufacture
cursor_manufacture = conn.cursor()

# Tabel untuk prodtype
cursor_prodtype = conn.cursor()

# Tabel untuk node similarity
cursor_nodesimilarity = conn.cursor()

# Tabel untuk knn fastrp
cursor_knn_fastrp = conn.cursor()

# Tabel untuk knn node2vec
cursor_knn_node2vec = conn.cursor()


# Membagi query dan membuat kondisi
def split_query(keyword):
    qlist = keyword.lower().split()
    cond = " OR ".join([f"foodproduct1 LIKE '%{q}%'" for q in qlist])
    return qlist, cond


# Menghitung Jaccard Similarity
def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return float(len(s1.intersection(s2)) / len(s1.union(s2)))


# Mengurutkan hasil berdasarkan Jaccard Similarity
def sort_results(resp, klist):
    resp.sort(key=lambda x: jaccard_similarity(x[1].lower().split(), klist), reverse=True)
    return resp


# Mengumpulkan Rekomendasi
def get_recommendation(k, etype):
    emb_sim = "knn_fastrp" if etype == "fastrp" else ("knn_node2vec" if etype == "node2vec" else "nodesimilarity")

    cursor_knn_fastrp.execute(f"""
    SELECT id1, foodproduct2 FROM {emb_sim}
    WHERE {split_query(k)[1]}
    ORDER BY id1, similarity DESC
    """)
    rec = cursor_knn_fastrp.fetchall()

    rlist = defaultdict(list)
    for num, value in rec:
        rlist[num].append(value)
    rc = dict(rlist)
    rec_dict = {key: " • ".join([f"{i}) {val}" for i, val in enumerate(values, start=1)]) for key, values in rc.items()}
    recommendation = pd.DataFrame(rec_dict.items(), columns=['ID', 'Rekomendasi'])
    return recommendation


# Mendapatkan respons berdasarkan kata kunci yang dimasukkan
def get_response(k):
    cursor_foodproduct.execute(f"""
    SELECT
        foodproduct.f_id,
        foodproduct.NamaProduk AS foodproduct1,
        manufacture.NamaPu,
        brand.MerekDagang,
        prodtype.NamaJenisProduk,
        certificate.NoSert
    FROM foodproduct
    LEFT JOIN manufacture ON foodproduct.m_id = manufacture.m_id
    LEFT JOIN brand ON foodproduct.b_id = brand.b_id
    LEFT JOIN prodtype ON foodproduct.p_id = prodtype.p_id
    LEFT JOIN certificate ON foodproduct.c_id = certificate.c_id
    WHERE {split_query(k)[1]}
    """)
    res = cursor_foodproduct.fetchall()

    result = sort_results(res, split_query(k)[0])
    response = pd.DataFrame(result, columns=['ID', 'Produk', 'Penyedia', 'Merk', 'Jenis', 'Sertifikat'])
    return response


st.title("Assalamualaikum. Selamat datang di Pencarian Produk dan Penyedia Makanan Halal Surabaya.")
search = st.text_input("Masukkan kata kunci produk halal di sini...")
embedding_type = st.selectbox("Pilih jenis embedding:", ["", "fastrp", "node2vec"])
lim = st.number_input("Masukkan jumlah baris yang ingin ditampilkan:", min_value=0, step=1)

if st.button("Cari", type='primary'):
    if search:
        st.write(f"Hasil pencarian **{search}**")
        hasil = get_response(search)
        rekomendasi = get_recommendation(search, embedding_type)
        hasil = pd.merge(hasil, rekomendasi, on=["ID"], how='left')
        hasil = hasil.drop("ID", axis=1)
        hasil.index += 1

        if not hasil.empty:
            st.caption(f"Menampilkan {min(lim, len(hasil))} dari total {len(hasil)} hasil.")
            st.table(hasil[:lim])
        else:
            st.error("Tidak ada hasil yang ditemukan.")
    else:
        st.warning("Masukkan kata kunci.")

st.subheader("Dipersembahkan oleh:")
st.image("logo.png")
