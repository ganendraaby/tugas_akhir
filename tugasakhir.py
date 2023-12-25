import streamlit as st
import sqlite3
import pandas as pd

# Menghubungkan ke database SQLite
conn = sqlite3.connect('halal_db.db')

# Menghubungkan ke semua tabel
cursor_tables = conn.cursor()


# Membagi query dan membuat kondisi
def split_query(keyword):
    qlist = keyword.lower().split()
    cond = " OR ".join([f"NamaProduk LIKE '%{q}%'" for q in qlist])
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


# Mendapatkan respons berdasarkan kata kunci yang dimasukkan
def get_response(k):
    cursor_tables.execute(f"""
    SELECT
        foodproduct.f_id,
        foodproduct.NamaProduk,
        manufacture.NamaPu,
        manufacture.AlamatPu,
        manufacture.KotaPu,
        manufacture.ProvPu,
        manufacture.KodePosPu,
        prodtype.NamaJenisProduk,
        brand.MerekDagang,
        brand.JmlProduk,
        certificate.NoSert,
        certificate.NoDaftar,
        certificate.TglDaftar,
        certificate.TglSert,
        certificate.TglValid
    FROM foodproduct
    LEFT JOIN manufacture ON foodproduct.m_id = manufacture.m_id
    LEFT JOIN prodtype ON foodproduct.p_id = prodtype.p_id
    LEFT JOIN brand ON foodproduct.b_id = brand.b_id
    LEFT JOIN certificate ON foodproduct.c_id = certificate.c_id
    WHERE {split_query(k)[1]}
    """)
    res = cursor_tables.fetchall()

    result = sort_results(res, split_query(k)[0])
    response = pd.DataFrame(result, columns=['ID', 'Produk', 'Nama Penyedia', 'Alamat', 'Kota', 'Provinsi', 'Kode Pos',
                                             'Jenis Produk', 'Merk Dagang', 'Jumlah Produk', 'Nomor Sertifikat',
                                             'Nomor Daftar', 'Tanggal Daftar', 'Tanggal Sertifikat', 'Tanggal Valid'])
    return response


# Mengumpulkan data rekomendasi
def get_recommendation(etype, product_id):
    emb_sim = "knn_fastrp" if etype == "fastrp" else ("knn_node2vec" if etype == "node2vec" else "nodesimilarity")

    cursor_tables.execute(f"""
    SELECT 
        {emb_sim}.id1,
        foodproduct.NamaProduk,
        manufacture.NamaPu,
        prodtype.NamaJenisProduk,
        brand.MerekDagang,
        certificate.NoSert
    FROM {emb_sim}
    LEFT JOIN foodproduct ON {emb_sim}.id2 = foodproduct.f_id
    LEFT JOIN manufacture ON foodproduct.m_id = manufacture.m_id
    LEFT JOIN prodtype ON foodproduct.p_id = prodtype.p_id
    LEFT JOIN brand ON foodproduct.b_id = brand.b_id
    LEFT JOIN certificate ON foodproduct.c_id = certificate.c_id
    WHERE id1 = {product_id}
    ORDER BY id1, similarity DESC
    """)
    rec = cursor_tables.fetchall()

    recommendation = pd.DataFrame(rec, columns=['ID', 'Produk', 'Penyedia', 'Jenis', 'Merk', 'Sertifikat'])
    return recommendation


st.title("Assalamualaikum. Selamat datang di Pencarian Produk dan Penyedia Makanan Halal Surabaya.")
search = st.text_input("Masukkan kata kunci produk halal di sini:")
embedding_type = st.selectbox("Pilih jenis embedding:", ["", "fastrp", "node2vec"])
lim = st.number_input("Masukkan jumlah baris yang ingin ditampilkan:", min_value=0, step=1)

if st.button("Cari", type='primary'):
    if search:
        st.write(f"Hasil pencarian **{search}**")
        hasil = get_response(search)
        hasil.index += 1

        if not hasil.empty:
            st.caption(f"Menampilkan {min(lim, len(hasil))} dari total {len(hasil)} hasil")
            
            for i in range(min(lim, len(hasil))):
                tab1, tab2, tab3, tab4 = st.tabs(["Jenis Produk dan Merk", "Penyedia", "Sertifikat", "Rekomendasi"])
                with tab1:
                    st.subheader(f"{i + 1}) {hasil.iloc[i]['Produk']}")
                    st.table(hasil.iloc[i, [7, 8, 9]].astype(str))
                with tab2:
                    st.subheader(f"{i + 1}) {hasil.iloc[i]['Produk']}")
                    st.table(hasil.iloc[i, [2, 3, 4, 5, 6]].astype(str))
                with tab3:
                    st.subheader(f"{i + 1}) {hasil.iloc[i]['Produk']}")
                    st.table(hasil.iloc[i, [10, 11, 12, 13, 14]].astype(str))
                with tab4:
                    st.subheader(f"Rekomendasi untuk {hasil.iloc[i]['Produk']}")
                    rekomendasi = get_recommendation(embedding_type, hasil.iloc[i]['ID'])
                    rekomendasi = rekomendasi.drop('ID', axis=1)
                    rekomendasi.index += 1
                    st.table(rekomendasi)
        else:
            st.error("Tidak ada hasil yang ditemukan.")
    else:
        st.warning("Masukkan kata kunci.")

st.subheader("Dipersembahkan oleh:")
st.image("logo.png")
