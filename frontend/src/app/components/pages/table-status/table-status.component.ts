import { Component, OnInit, Inject, PLATFORM_ID, NgZone } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';
import { TableStatusService } from '../../../service/table-status.service';
import Swal from 'sweetalert2';
import { lastValueFrom } from 'rxjs';
import { isPlatformBrowser } from '@angular/common';
import { LoginService } from '../../../service/login.service';

@Component({
  selector: 'app-table-status',
  standalone: false,
  templateUrl: './table-status.component.html',
  styleUrl: './table-status.component.css'
})
export class TableStatusComponent implements OnInit {
  qrCodes: { [key: number]: any } = {};
  tables: any;
  payment: any;
  selectedTable: any = null;
  paymentTotal: number = 0;
  qrCodeUrl: any = null;
  order: any;

  constructor(private tableStatusService: TableStatusService, private sanitizer: DomSanitizer, 
    @Inject(PLATFORM_ID) private platformId: Object, private ngZone: NgZone,
    private loginService: LoginService) {}

  ngOnInit(): void {
    this.tableStatusService.getAllTable().subscribe((res) => {
      this.tables = res;
      console.log(this.tables);
      
      this.tables.forEach((t: any) => {
        if (t.code) {
          // const qrData = `kmitlcafe.sirawit.in.th/ordering/1/${t.code}`;
          const qrData = `https://kmitlcafe.sirawit.in.th:4200/ordering/1/${t.code}`;
          t.url = qrData
          t.image = this.sanitizer.bypassSecurityTrustUrl(
            `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(qrData)}&size=200x200`
          ); 
        } else {
          t.image = null
        }
      });
    });

    this.tableStatusService.getAllPayment().subscribe((res) => {
      this.payment = res;
      console.log(this.payment);
    });

    this.tableStatusService.getAllOrder().subscribe((res) => {
      this.order = res;
      console.log(this.order);
    });
  }

  async fetchOrderAndPayment(): Promise<void> {
    try {
      const [paymentRes, orderRes] = await Promise.all([
        lastValueFrom(this.tableStatusService.getAllPayment()),
        lastValueFrom(this.tableStatusService.getAllOrder())
      ]);
      this.payment = paymentRes;
      this.order = orderRes;
      console.log("อัปเดตข้อมูล Payment และ Order แล้ว:", this.payment, this.order);
    } catch (err) {
      console.error("ไม่สามารถโหลดข้อมูล payment/order ได้:", err);
    }
  }

  async updateTable(table: any) {
    if (!table.people || Number(table.people) <= 0) {
      Swal.fire('ข้อผิดพลาด', 'กรุณาระบุจำนวนลูกค้าที่ถูกต้อง!', 'error');
      return;
    }
  
    if (!table.status || (table.status !== 'enable' && table.status !== 'disable')) {
      Swal.fire('ข้อผิดพลาด', 'กรุณาเลือกสถานะโต๊ะที่ถูกต้อง!', 'error');
      return;
    }
  
    const confirmResult = await Swal.fire({
      title: 'ยืนยันการเปลี่ยนสถานะ',
      text: `คุณต้องการเปลี่ยนสถานะโต๊ะเป็น "${table.status}" ใช่หรือไม่?`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'ยืนยัน',
      cancelButtonText: 'ยกเลิก'
    });
  
    if (!confirmResult.isConfirmed) return;
  
    // อัปเดตข้อมูล Payment และ Order ก่อนตรวจสอบ
    await this.fetchOrderAndPayment();
  
    const relatedOrder = this.order.find((o: any) => o.table_id === table.table_id);
    if (table.status === 'disable' && relatedOrder) {
      if (!relatedOrder.payment_id) {
        await Swal.fire('ไม่สามารถปิดโต๊ะได้', 'ลูกค้ายังไม่ได้ชำระเงิน กรุณาชำระเงินก่อนปิดโต๊ะ', 'warning');
        return;
      }
  
      // ตรวจสอบ payment_method ว่ายังเป็น null หรือไม่
      const paymentInfo = this.payment.find((p: any) => p.payment_id === relatedOrder.payment_id);
      if (!paymentInfo || paymentInfo.payment_status === 0) {
        await this.selectPaymentMethod(table);
  
        // อัปเดตข้อมูลอีกครั้งหลังเลือกช่องทางชำระเงิน
        await this.fetchOrderAndPayment();
  
        const updatedPayment = this.payment.find((p: any) => p.payment_id === relatedOrder.payment_id);
        if (!updatedPayment || updatedPayment.payment_method === null) {
          await Swal.fire('ไม่สามารถปิดโต๊ะได้', 'กรุณาชำระเงินก่อน', 'warning');
          return;
        }
      }
    }
  
    // อัปเดตสถานะโต๊ะ
    this.tableStatusService.updateTableStatus(table).subscribe(
      (res: any) => {
        Swal.fire('สำเร็จ', `โต๊ะ ${table.table_id} ถูกอัปเดตแล้ว`, 'success');
  
        this.tableStatusService.getAllTable().subscribe((res) => {
          this.tables = res;
          this.tables.forEach((t: any) => {
            if (t.code) {
              const qrData = `https://kmitlcafe.sirawit.in.th:4200/ordering/1/${t.code}`;
              t.url = qrData;
              t.image = this.sanitizer.bypassSecurityTrustUrl(
                `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(qrData)}&size=200x200`
              );
            } else {
              t.image = null;
            }
          });
        });
      },
      (err) => {
        Swal.fire('ล้มเหลว', 'ไม่สามารถอัปเดตสถานะโต๊ะได้', 'error');
        console.error(err);
      }
    );
  }  
  
  setSelectedTable(tableId: number) {
    localStorage.setItem('selectedTableId', tableId.toString());
    console.log(`บันทึกโต๊ะที่เลือก: ${tableId}`);
  }

  refreshTableData() {
    this.tableStatusService.getAllTable().subscribe((res) => {
      this.tables = res;
      console.log("ข้อมูลโต๊ะที่โหลดใหม่:", this.tables);
  
      // โหลด QR Code ใหม่ ไม่ใช้ค่าที่อาจผิดพลาดจาก LocalStorage
      this.tables.forEach((t: any) => {
        const storedCode = localStorage.getItem(`table_qr_${t.table_id}`);
        if (storedCode) {
          // const qrData = `kmitlcafe.sirawit.in.th/ordering/1/${storedCode}`;
          const qrData = `https://kmitlcafe.sirawit.in.th:4200/ordering/1/${storedCode}`;
          this.qrCodes[t.table_id] = this.sanitizer.bypassSecurityTrustUrl(
            `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(qrData)}&size=200x200`
          );
        }
      });
    });
  }  
  
  async selectPaymentMethod(table: any) {
    await this.fetchOrderAndPayment();
    // หา payment_id ที่ตรงกับโต๊ะที่เลือก
    const order = this.order.find((o: any) => o.table_id === table.table_id);
    
    if (!order || !order.payment_id) {
      Swal.fire('ข้อผิดพลาด', 'ไม่พบข้อมูลการชำระเงินของโต๊ะนี้', 'error');
      return;
    }
  
    const { value: paymentMethod } = await Swal.fire({
      title: 'เลือกช่องทางชำระเงิน',
      html: `
        <div style="display: flex; flex-direction: column; gap: 10px;">
          <button id="cashBtn" class="swal2-confirm swal2-styled" style="background-color: #ffcc00; color: #000; padding: 10px;">เงินสด</button>
          <button id="creditBtn" class="swal2-confirm swal2-styled" style="background-color: #007bff; color: #fff; padding: 10px;">บัตรเครดิต</button>
          <button id="qrBtn" class="swal2-confirm swal2-styled" style="background-color: #28a745; color: #fff; padding: 10px;">QR PromptPay</button>
        </div>
      `,
      showCancelButton: true,
      showConfirmButton: false,
      cancelButtonText: 'ยกเลิก',
      didOpen: () => {
        document.getElementById('cashBtn')?.addEventListener('click', () => Swal.close({ value: 'Cash' }));
        document.getElementById('creditBtn')?.addEventListener('click', () => Swal.close({ value: 'CreditCard' }));
        document.getElementById('qrBtn')?.addEventListener('click', () => Swal.close({ value: 'PromptPay' }));
      }
    });
  
    if (paymentMethod) {
      if (paymentMethod === 'PromptPay') {
        await this.openPaymentModal(table, order.payment_id);
      } else {
        await this.processPayment(order.payment_id, paymentMethod);
      }
    }
  }
  
  async processPayment(paymentId: number, paymentMethod: string): Promise<void> {
    console.log('ส่งข้อมูลยืนยันการชำระเงิน:', {
      payment_id: paymentId,
      payment_method: paymentMethod
    });
  
    try {
      await lastValueFrom(this.tableStatusService.makePayment(paymentId, paymentMethod));
      Swal.fire('สำเร็จ', 'การชำระเงินได้รับการยืนยันแล้ว!', 'success');
    } catch (error) {
      console.error('เกิดข้อผิดพลาดในการยืนยันการชำระเงิน:', error);
      Swal.fire('ยืนยันล้มเหลว', 'ไม่สามารถยืนยันการชำระเงินได้', 'error');
    }
  }
  
  openPaymentModal(table: any, paymentId: number) {
    console.log("Table ID:", table.table_id, "Payment ID:", paymentId);
  
    return this.tableStatusService.getPaymentTotalByTable(table.table_id).subscribe(
      (res: any) => {
        console.log("Payment Data:", res);
        if (res.total_price) {
          this.paymentTotal = res.total_price;
          const phoneNumber = "0632142555";
          const qrUrl = `https://promptpay.io/${phoneNumber}/${this.paymentTotal}.png`;
  
          this.qrCodeUrl = this.sanitizer.bypassSecurityTrustUrl(qrUrl);
          this.selectedTable = table;
  
          return Swal.fire({
            title: '🔹 สแกน QR เพื่อชำระเงิน',
            html: `<div class="text-center">
                    <p>ยอดชำระทั้งหมด: <b>${this.paymentTotal} บาท</b></p>
                    <img src="${qrUrl}" alt="QR PromptPay" width="200">
                   </div>`,
            showCancelButton: true,
            confirmButtonText: 'ยืนยันการชำระ',
            cancelButtonText: 'ยกเลิก',
            preConfirm: () => this.processPayment(paymentId, "PromptPay"),
            allowOutsideClick: () => !Swal.isLoading(),
          });
        } else {
          return Swal.fire('ข้อผิดพลาด', 'ไม่พบยอดรวมสำหรับโต๊ะนี้', 'error');
        }
      },
      (error) => {
        console.error('Error fetching total price:', error);
        return Swal.fire('ข้อผิดพลาด', 'ไม่สามารถดึงยอดรวมได้', 'error');
      }
    );
  }  
  
}
