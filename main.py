from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.metrics import dp
from jnius import autoclass
from android.permissions import request_permissions, Permission
import os

# Android классы
MediaMetadataRetriever = autoclass('android.media.MediaMetadataRetriever')
Intent = autoclass('android.content.Intent')
Uri = autoclass('android.net.Uri')
PythonActivity = autoclass('org.kivy.android.PythonActivity')
DocumentsContract = autoclass('android.provider.DocumentsContract')
Toast = autoclass('android.widget.Toast')

class LastFrameApp(App):
    def build(self):
        Window.clearcolor = (0.05, 0.05, 0.1, 1)
        self.main_layout = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(30))

        title = Label(
            text='LastFrame',
            font_size='42sp',
            color=(0, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(80)
        )

        instr = Label(
            text='[b]Как пользоваться:[/b]\n\n'
                 '1. Открой любое видео\n'
                 '2. Нажми «Поделиться»\n'
                 '3. Выбери [color=00ffaa]LastFrame[/color]\n'
                 '4. Укажи папку — и последний кадр твой!\n\n'
                 'Приложение закроется само после сохранения.',
            markup=True,
            font_size='20sp',
            color=(0.9, 0.9, 0.9, 1),
            text_size=(Window.width - dp(60), None),
            halign='center'
        )

        self.main_layout.add_widget(title)
        self.main_layout.add_widget(instr)

        return self.main_layout

    def on_start(self):
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE
        ])
        # Проверяем, запущено ли через "поделиться"
        activity = PythonActivity.mActivity
        intent = activity.getIntent()
        if intent.getAction() == Intent.ACTION_SEND and intent.getType() and intent.getType().startswith('video/'):
            uri = intent.getParcelableExtra(Intent.EXTRA_STREAM)
            if uri:
                self.process_shared_video(uri)

    def process_shared_video(self, uri):
        # Получаем реальный путь
        try:
            context = PythonActivity.mActivity
            cursor = context.getContentResolver().query(uri, None, None, None, None)
            cursor.moveToFirst()
            path = cursor.getString(cursor.getColumnIndexOrThrow("_data"))
            cursor.close()
        except:
            self.show_toast("Ошибка доступа к файлу")
            PythonActivity.mActivity.finish()
            return

        self.video_path = path
        # Убираем инструкцию и просим выбрать папку
        self.main_layout.clear_widgets()
        waiting = Label(
            text='Выбери папку для сохранения\nпоследнего кадра...',
            font_size='26sp',
            color=(0, 1, 0.8, 1)
        )
        self.main_layout.add_widget(waiting)

        intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        PythonActivity.mActivity.startActivityForResult(intent, 999)

    def on_activity_result(self, requestCode, resultCode, intent):
        if requestCode == 999 and resultCode == -1 and intent:
            tree_uri = intent.getData()

            retriever = MediaMetadataRetriever()
            retriever.setDataSource(self.video_path)
            bitmap = retriever.getFrameAtTime(-1, MediaMetadataRetriever.OPTION_CLOSEST)
            retriever.release()

            if not bitmap:
                self.show_toast("Не удалось извлечь кадр")
                return

            name = os.path.basename(self.video_path)
            name = os.path.splitext(name)[0] + "_last.jpg"

            context = PythonActivity.mActivity.getApplicationContext()
            doc_uri = DocumentsContract.createDocument(
                context.getContentResolver(),
                tree_uri,
                "image/jpeg",
                name
            )

            if doc_uri:
                out = context.getContentResolver().openOutputStream(doc_uri)
                bitmap.compress(bitmap.CompressFormat.JPEG, 97, out)
                out.close()
                self.show_toast(f"Готово!\n{name}")
            else:
                self.show_toast("Ошибка сохранения")

            # Закрываем приложение через 2 секунды
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: PythonActivity.mActivity.finish(), 2)

    def show_toast(self, text):
        Toast.makeText(PythonActivity.mActivity, text, Toast.LENGTH_LONG).show()

LastFrameApp().run()
