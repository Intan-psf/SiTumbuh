import { GoogleGenerativeAI } from "@google/generative-ai";

const businessInfo = `
Nama Website: SiTumbuh
Lokasi: Universitas Negeri Semarang Sekaran, Kec. Gn. Pati, Kota Semarang, Jawa Tengah 50229 
Email: ifrombel1@gmail.com

Apa itu Si Tumbuh?
Si Tumbuh adalah sebuah platform digital yang dirancang untuk membantu mencegah stunting di Indonesia. Melalui pendekatan teknologi yang terintegrasi, platform ini memberikan edukasi dan layanan interaktif seputar kesehatan anak dan gizi. Si Tumbuh dilengkapi dengan berbagai fitur utama seperti prediksi risiko stunting yang membantu orang tua mengenali potensi masalah sejak dini, serta chatbot virtual bernama RAISA (Ramah Informasi Seputar Anak) yang siap memberikan informasi dan menjawab pertanyaan seputar tumbuh kembang anak dengan gaya yang ramah dan mudah dipahami. Selain itu, tersedia pula fitur informasi posyandu untuk mengetahui jadwal dan lokasi pelayanan terdekat, serta layanan konsultasi dengan dokter agar pengguna dapat memperoleh saran medis yang terpercaya. Dengan fitur-fitur tersebut, Si Tumbuh hadir sebagai pendamping keluarga dalam memastikan anak-anak Indonesia tumbuh sehat, cerdas, dan optimal.

FAQs untuk Chat Assitance
Apa itu stunting dan mengapa penting untuk memantau?
Stunting adalah gangguan pertumbuhan pada anak akibat malnutrisi, yang dapat berdampak pada perkembangan jangka panjang. Memantau stunting penting untuk memastikan intervensi dini agar anak tumbuh sehat.

Bagaimana cara kerja alat prediksi stunting?
Alat prediksi stunting kami menganalisis data seperti usia, tinggi badan, berat badan, dan pola makan untuk memberikan gambaran kemungkinan stunting pada anak.

Apa yang harus dilakukan jika anak saya berisiko stunting?
Kami menyarankan untuk meningkatkan pola makan anak, mengikuti acara Posyandu, serta berkonsultasi dengan tenaga medis untuk langkah lebih lanjut.

Seberapa sering acara Posyandu diselenggarakan?
Acara Posyandu diadakan secara rutin. Silakan cek situs web kami untuk informasi acara berikutnya di lokasi Anda.

Jenis rekomendasi obat apa yang diberikan?
Kami memberikan rekomendasi suplemen gizi dan intervensi kesehatan lainnya berdasarkan prediksi stunting dan pedoman kesehatan umum.

Dimana lokasi fisik Anda?
Kami berada di Universitas Negeri Semarang Sekaran, Kec. Gn. Pati, Kota Semarang, Jawa Tengah 50229. Anda juga bisa mengunjungi situs web kami untuk informasi lebih lanjut.

Bagaimana cara menghubungi Anda untuk informasi lebih lanjut?
Anda dapat menghubungi kami melalui atau email di ifrombel1@gmail.com. Kami siap membantu menjawab pertanyaan Anda.

Apa kebijakan pengembalian Anda?
Saat ini, kami tidak memiliki kebijakan pengembalian untuk layanan. Namun, jika Anda memiliki pertanyaan atau masalah, silakan hubungi kami untuk penyelesaian yang cepat.

Apakah data pribadi saya aman?
Ya, kami menjaga keamanan data pribadi Anda. Semua data disimpan dengan aman dan hanya digunakan untuk memberikan rekomendasi kesehatan yang akurat.

Bagaimana cara mendaftar untuk acara Posyandu?
Pendaftaran sangat mudah! Kunjungi situs web kami, pilih acara yang Anda minati, dan isi formulir pendaftaran secara online.
`;
const API_KEY = "AIzaSyC77Kh55oJ9PbE_xw04fRT-Rs5z7uBVdMU";
const genAI = new GoogleGenerativeAI(API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash", systemInstruction: businessInfo });

let chat;

async function initChat() {
  chat = await model.startChat({
    history: [
      { role: "user", parts: [{ text: "Hello" }] },
      { role: "model", parts: [{ text: "Halo, ada yang bisa saya bantu?" }] },
    ],
  });
}

async function sendMessage() {
  try {
    const input = document.querySelector(".chat-window input");
    const message = input.value.trim();

    if (!navigator.onLine) {
      document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
        <div class="error"><p>Terjadi kesalahan! Anda sedang offline, pesan belum terkirim.</p></div>
      `);
      return;
    }

    if (message) {
      input.value = "";

      document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
        <div class="user"><p>${message}</p></div>
        <div class="loader"></div>
      `);

      scrollToBottom();

      const result = await chat.sendMessage(message);

      try {
        const response = await result.response;
        const text = await response.text();

        document.querySelector(".chat-window .chat .loader").remove();

        document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
          <div class="model"><p>${text}</p></div>
        `);

        scrollToBottom();
      } catch (err) {
        document.querySelector(".chat-window .chat .loader").remove();
        document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
          <div class="error"><p>Terjadi kesalahan saat membaca response!</p></div>
        `);
      }
    }
  } catch (error) {
    console.error("Error saat mengirim pesan:", error);

    const loader = document.querySelector(".chat-window .chat .loader");
    if (loader) loader.remove();

    document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
    <div class="error"><p>Terjadi kesalahan saat membaca response!</p></div>
    `);
  }
}

function scrollToBottom() {
  const chatBox = document.querySelector(".chat-window .chat");
  chatBox.scrollTop = chatBox.scrollHeight;
}

document.addEventListener("DOMContentLoaded", async () => {
  await initChat();

  const sendButton = document.querySelector(".chat-window .input-area button");
  const inputField = document.querySelector(".chat-window input");

  sendButton.addEventListener("click", () => sendMessage());

  inputField.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }
  });

    const chatBtn = document.querySelector(".chat-button");
    const chatWindow = document.querySelector(".chat-window");
    const closeBtn = document.querySelector(".chat-window .close");

    chatBtn.addEventListener("click", () => {
      document.body.classList.add("chat-open");
      chatWindow.classList.add("show");
    });

    closeBtn.addEventListener("click", () => {
      document.body.classList.remove("chat-open");
      chatWindow.classList.remove("show");
    });
});
