import { TableStatusComponent } from './../pages/table-status/table-status.component';
import { Component, OnInit, Inject, PLATFORM_ID, NgZone } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormControl, FormGroup } from '@angular/forms';
import { ChangeDetectorRef } from '@angular/core';
import { OrderingService } from '../../service/ordering.service';
import Swal from 'sweetalert2';
import { TokenStorageService } from '../../service/token-storage.service';
import { TableStatusService } from '../../service/table-status.service';

@Component({
  selector: 'app-ordering',
  standalone: false,
  
  templateUrl: './ordering.component.html',
  styleUrl: './ordering.component.css'
})
export class OrderingComponent implements OnInit{
  menu_types: any;
  isLoggedIn = false;
  id: any;
  code: any;
  menu_by_type_id: any;
  category: any;
  menu_modalForm!: FormGroup;
  cartItems: any[] = [];
  number: number = 0;
  user: any;
  table: any;
  tableByCode: any;
  tableCode: any;
  tableOrders: any[] = [];
  isLoadingMenus: boolean = false;



  constructor(private router: Router, private route: ActivatedRoute, private service_order: OrderingService, private cdr: ChangeDetectorRef, private tokenStorage: TokenStorageService,
    private tableService : TableStatusService, @Inject(PLATFORM_ID) private platformId: Object, private ngZone: NgZone)
  { 
    this.menu_modalForm = new FormGroup({
      id: new FormControl(null),
      image: new FormControl(),
      name: new FormControl(),
      des: new FormControl(),
      price: new FormControl(),
      qty: new FormControl(1), 
      note: new FormControl(''), 
    });    
  }

  ngOnInit(): void {
    this.isLoadingMenus = true;
    this.service_order.getAllMenuTypes().subscribe((res) => {
      this.menu_types = res;
      console.log(this.menu_types);
    });

    this.isLoggedIn = !!this.tokenStorage.getToken();
    this.code = this.route.snapshot.paramMap.get('code');
    console.log('QR Code:', this.code);

    if (this.code) {
      this.verifyTableCode();
    }

    this.tableService.getTableByCode(this.code).subscribe((res)=>{
      this.table = res
      this.tableByCode = res.table_id
      this.tableCode = res.code

      console.log("Table ID : ",this.tableByCode)
      console.log("Table Code : ", this.tableCode);

      if (this.tableByCode) {
        this.getTableOrders(this.tableByCode);
      }
    })

    this.loadCartFromLocalStorage();
    this.id = this.route.snapshot.paramMap.get('id')
    
    this.service_order.getAllMenusById(this.id).subscribe((res)=>{
      this.menu_by_type_id = res
      console.log(this.menu_by_type_id);
    })

    this.service_order.getCategoryById(this.id).subscribe((res)=>{
      this.category = res
      console.log(this.category);
    })
    this.isLoadingMenus = false;

    if (isPlatformBrowser(this.platformId) && typeof window !== 'undefined') {
      this.ngZone.runOutsideAngular(() => {
        setInterval(() => {
          this.ngZone.run(() => {
            this.getTableOrders(this.tableByCode);
          });
        }, 5000);
      });
    }  
  }

  verifyTableCode() {
    this.service_order.verifyTableCode(this.code).subscribe(
      (response) => {
        console.log('QR Code Verified:', response);
      },
      (error) => {
        Swal.fire('ข้อผิดพลาด', 'รหัส QR ไม่ถูกต้องหรือโต๊ะถูกปิดใช้งาน', 'error').then((err) => {
          console.log(err)
          this.router.navigate(['/']);
        });
      }
    );
  }

  selectMenuTypesById(id: any) {
    this.isLoadingMenus = true;
      if (this.tableByCode && this.tableCode) {
        let url = `/ordering/${id}/${this.tableCode}`;
        console.log('Navigating to:', url);
    
        this.router.navigateByUrl('/', { skipLocationChange: true }).then(() => {
          this.router.navigate([url]);
        });
        this.isLoadingMenus = false;
      } else {
        Swal.fire('ข้อผิดพลาด', 'ไม่พบ QR Code ของโต๊ะ!', 'error');
        this.isLoadingMenus = false;
      }
    }  

  sendMenuToCart(menu:any): void {
    this.menu_modalForm.controls['id'].setValue(menu.id);
    this.menu_modalForm.controls['image'].setValue(menu.image);
    this.menu_modalForm.controls['name'].setValue(menu.name);
    this.menu_modalForm.controls['des'].setValue(menu.des);
    this.menu_modalForm.controls['price'].setValue(menu.price);
    this.menu_modalForm.controls['qty'].setValue(1);
    this.menu_modalForm.controls['note'].setValue(''); 
    console.log(menu)
  }

  addToCart(): void {
    const cartItem = {
      id: this.menu_modalForm.value.id,
      image: this.menu_modalForm.value.image,
      name: this.menu_modalForm.value.name,
      price: this.menu_modalForm.value.price,
      qty: this.menu_modalForm.value.qty || 1,
      note: (document.getElementById('menuNote') as HTMLTextAreaElement).value,
    };
  
    Swal.fire({
      title: 'เพิ่มเมนูนี้ลงในตะกร้า?',
      html: `<strong>${cartItem.name}</strong><br>ราคา: ${cartItem.price} บาท<br>จำนวน: ${cartItem.qty}<br>หมายเหตุ: ${cartItem.note || 'ไม่มี'}`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'ใช่, เพิ่มเลย',
      cancelButtonText: 'ยกเลิก',
    }).then((result) => {
      if (result.isConfirmed) {
        const existingItem = this.cartItems.find(
          (item) => item.id === cartItem.id && item.note === cartItem.note
        );
  
        if (existingItem) {
          existingItem.qty += cartItem.qty;
        } else {
          this.cartItems.push(cartItem);
        }
  
        this.saveCartToLocalStorage();
        this.cdr.detectChanges();
  
        Swal.fire('เพิ่มเมนูเรียบร้อย', 'เมนูถูกเพิ่มในตะกร้าแล้ว!', 'success');
        console.log('เพิ่มสินค้าในตะกร้า:', cartItem);
        console.log('รายการทั้งหมดในตะกร้า:', this.cartItems);
      }
    });
  }    

  increaseQty(index: number): void {
    const currentQty = this.menu_modalForm.value.qty || 1;
    this.menu_modalForm.controls['qty'].setValue(currentQty + 1);
    // แสดงข้อมูลใน console
    console.log('เพิ่มจำนวนสินค้าในตะกร้า:', this.cartItems[index]);
    console.log('รายการทั้งหมดในตะกร้า:', this.cartItems);
  }

  decreaseQty(index: number): void {
    const currentQty = this.menu_modalForm.value.qty || 1;
    if (currentQty > 1) {
      this.menu_modalForm.controls['qty'].setValue(currentQty - 1);
    }
    // แสดงข้อมูลใน console
    console.log('ลดจำนวนสินค้าในตะกร้า:', this.cartItems[index]);
    console.log('รายการทั้งหมดในตะกร้า:', this.cartItems);
  }

  getTotalPrice(): number {
    return this.cartItems.reduce(
      (total, item) => total + item.price * item.qty,
      0
    );
  }

  saveCartToLocalStorage(): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cartItems', JSON.stringify(this.cartItems));
    } else {
      console.warn('localStorage is not available. Data will not be saved.');
    }
  }  

  loadCartFromLocalStorage(): void {
    if (typeof localStorage !== 'undefined') {
      const storedCart = localStorage.getItem('cartItems');
      if (storedCart) {
        this.cartItems = JSON.parse(storedCart);
        console.log('โหลดข้อมูลตะกร้าจาก Local Storage:', this.cartItems);
      }
    } else {
      console.warn('localStorage is not available.');
    }
  }  

  removeFromCart(index: number): void {
    const item = this.cartItems[index];
  
    Swal.fire({
      title: 'คุณต้องการลบเมนูนี้ออกจากตะกร้า?',
      html: `<strong>${item.name}</strong><br>จำนวน: ${item.qty}<br>หมายเหตุ: ${item.note || 'ไม่มี'}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'ใช่, ลบเลย',
      cancelButtonText: 'ยกเลิก',
    }).then((result) => {
      if (result.isConfirmed) {
        this.cartItems.splice(index, 1);
        this.saveCartToLocalStorage();
        console.log('ลบสินค้าออกจากตะกร้า:', item);
        Swal.fire('ลบเรียบร้อย', 'เมนูถูกนำออกจากตะกร้าแล้ว', 'success');
      }
    });
  }  

  confirmOrder(): void {
    if (this.cartItems.length === 0) {
      Swal.fire('ข้อผิดพลาด', 'กรุณาเพิ่มรายการสินค้าลงในตะกร้า!', 'error');
      return;
    }
  
    const tableId = this.tableByCode;
    const code = this.code;
  
    if (!tableId || !code) {
      Swal.fire('ข้อผิดพลาด', 'ไม่พบข้อมูลโต๊ะหรือ QR Code!', 'error');
      return;
    }
  
    const orderItems = this.cartItems.map(item => {
      return {
        id: item.id,
        qty: item.qty,
        note: item.note?.trim() || 'ไม่มี'
      };
    });
  
    const orderData = {
      code: code,
      people: "2",
      table: Number(tableId),
      items: orderItems,
      total_price: this.getTotalPrice(),
    };
  
    // แสดง SweetAlert เพื่อยืนยันก่อนส่ง order
    Swal.fire({
      title: 'ยืนยันการสั่งอาหาร?',
      html: `รวมทั้งหมด <strong>${orderData.total_price}</strong> บาท<br>จำนวน ${orderData.items.length} รายการ`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'ยืนยัน',
      cancelButtonText: 'ยกเลิก',
    }).then((result) => {
      if (result.isConfirmed) {
        console.log('ข้อมูลการสั่งซื้อที่ส่งไป API:', JSON.stringify(orderData, null, 2));
  
        this.service_order.createOrder(orderData).subscribe(
          (response) => {
            Swal.fire('ยืนยันคำสั่งเรียบร้อย', 'Your order has been placed successfully!', 'success');
            this.cartItems = [];
            this.saveCartToLocalStorage();
            this.getTableOrders(tableId);
          },
          (error) => {
            console.error('Error placing order:', error);
            Swal.fire('ข้อผิดพลาด', error.error.message || 'ไม่สามารถสั่งซื้อได้!', 'error');
          }
        );
      }
    });
  }  
  
  getTableOrders(tableId: number) {
    this.service_order.getOrderItemsByTable(tableId).subscribe(
      (res) => {
        this.tableOrders = res;
        console.log("Orders for table:", this.tableOrders);
      },
      (error) => {
        if (error.status === 404) {
          console.log("ไม่มีรายการอาหารที่สั่ง"); 
        } else {
          console.warn("เกิดข้อผิดพลาดในการดึงรายการอาหาร:", error); 
        }
        this.tableOrders = [];
      }
    );
  }

  getTotalOrderPrice(): number {
    return this.tableOrders.reduce((total, order) => {
      return total + order.orders_items.reduce((subTotal: any, item: { total: any; }) => subTotal + item.total, 0);
    }, 0);
  }
  
  getOrderStatus(status_order: number, status_serve: number): string {
    if (status_serve === 1) {
      return 'อาหารถูกเสิร์ฟแล้ว';
    }
  
    switch (status_order) {
      case 0:
        return 'กำลังเตรียม';
      case 1:
        return 'กำลังปรุงอาหาร';
      case 2:
        return 'อาหารพร้อมเสิร์ฟแล้ว';
      default:
        return 'สถานะไม่ระบุ';
    }
  }  
}