import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .views import get_current_summary_data # Import fungsi tadi

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "pantau_cukur_events"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Kirim data awal saat pertama kali konek
        summary_data = await self.get_summary_from_db()
        await self.send(text_data=json.dumps({
            'type': 'INITIAL_CONNECTION',
            'message': 'Koneksi Berhasil!',
            'data': summary_data
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Membungkus fungsi Django ORM agar aman dijalankan di Async
    @database_sync_to_async
    def get_summary_from_db(self):
        return get_current_summary_data()

    async def send_status_update(self, event):
        """
        Dipanggil saat ada event dari layer group.
        Kamera kirim status -> Backend simpan DB -> Backend trigger group_send -> Fungsi ini jalan.
        """
        # 1. Ambil info perubahan status kursi
        chair_id = event['chair_id']
        is_occupied = event['is_occupied']
        message = event['message']

        # 2. Ambil summary terbaru dari database setelah perubahan status tadi
        updated_summary = await self.get_summary_from_db()

        # 3. Kirim Paket Lengkap ke Frontend
        await self.send(text_data=json.dumps({
            'type': 'STATUS_UPDATE',
            'chair_id': chair_id,
            'is_occupied': is_occupied,
            'message': message,
            'updated_summary': updated_summary # Frontend tinggal templok data ini ke UI
        }))