import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { TestAIService } from '../../../service/test-ai.service';

@Component({
  selector: 'app-test-ai',
  standalone: false,
  templateUrl: './test-ai.component.html',
  styleUrl: './test-ai.component.css'
})
export class TestAIComponent implements OnInit{

  constructor(private cdr: ChangeDetectorRef, private service: TestAIService){}
  resp: any
  isRecording = false;
  mediaRecorder!: MediaRecorder;
  audioChunks: Blob[] = [];
  stream!: MediaStream;
  ngOnInit(): void {
    console.log(this.resp)
  }

  startRecording(): void {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("อุปกรณ์นี้ไม่รองรับการบันทึกเสียง");
      return;
    }

    this.resp = null;
    this.isRecording = true;
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        this.stream = stream;
        this.mediaRecorder = new MediaRecorder(stream);
        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = event => {
          this.audioChunks.push(event.data);
        };

        this.mediaRecorder.onstop = () => {
          console.log("หยุดบันทึกเสียงแล้ว...");
          const audioBlob = new Blob(this.audioChunks, { type: 'audio/mp3' });
          const audioFile = new File([audioBlob], 'speech.mp3', { type: 'audio/mp3' });

          const audioUrl = URL.createObjectURL(audioBlob);
          console.log("ไฟล์ที่บันทึก:", audioFile);
          console.log("ลิงก์เสียง:", audioUrl);

          const audio = new Audio(audioUrl);
          console.log("กดเล่นเสียง:", audio);
          audio.play();

          console.log("ไฟล์ที่บันทึก:", audioFile);
          this.uploadAudio(audioFile);
        };

        this.mediaRecorder.start();
        console.log("เริ่มบันทึกเสียง...");
      })
      .catch(error => {
        console.error("เกิดข้อผิดพลาดในการเข้าถึงไมโครโฟน:", error);
      });
  }

  stopRecording(): void {
    if (this.mediaRecorder && this.stream) {
      this.isRecording = false;
      this.mediaRecorder.stop();

      // หยุด stream ของไมโครโฟน
      this.stream.getTracks().forEach(track => track.stop());
      console.log("ปิดไมโครโฟนเรียบร้อย");
    }
  }

  uploadAudio(audioFile: File): void {
    console.log("กำลังส่งไฟล์เสียงไป API...");
    console.log("รายละเอียดไฟล์:", audioFile);
    this.service.uploadAudio(audioFile).subscribe({
      next: event => {
        if (event.body) {
          const body = typeof event.body === "string" ? JSON.parse(event.body) : event.body;
          console.log("ข้อมูลที่ได้รับจาก API:", body); // ตรวจสอบข้อมูล
          this.resp = body;
          console.log("ค่า resp ที่กำหนด:", this.resp); // ตรวจสอบค่า resp
          this.cdr.detectChanges(); // บังคับให้อัปเดต UI
        }
      },
        error: error => {
            console.error("เกิดข้อผิดพลาดในการอัปโหลดเสียง:", error);
        },
        complete: () => {
            console.log("อัปโหลดเสียงสำเร็จ");
        }
      }
    );
  }

}
