## saran untuk sistem roi penanda kursi 
sistem roi sudah memiliki kemampuan menggambar maual menggunakan mouse.
tapi kekurangnnya adalah, setelah menggambar kita tidak bisa mengupdate, menghapus dan menggeser kotak roi 

## saran umum 
- Modul vs Class: Saat ini kamu masih memakai fungsi-fungsi di utils.py. Jika nanti startupmu butuh menangkap banyak kamera sekaligus, fungsi-fungsi ini akan kewalahan. Kamu harus mulai memikirkan untuk membungkus main ke dalam sebuah class App.
- Robustness: Perhatikan bagian last_status[i] = new_status[i]. Itu adalah "jembatan" agar UI tidak flicker saat kamu menambah/menghapus kursi. Pastikan kamu paham alur datanya.