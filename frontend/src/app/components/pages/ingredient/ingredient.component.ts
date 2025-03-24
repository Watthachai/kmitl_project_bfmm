import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import Swal from 'sweetalert2';
import { IngredientService } from '../../../service/ingredient.service';
import { ActivatedRoute, Router } from '@angular/router';
import bootstrap from 'bootstrap';
import { environment } from '../../../../environments/environment.development';

@Component({
  selector: 'app-ingredient',
  standalone: false,
  templateUrl: './ingredient.component.html',
  styleUrl: './ingredient.component.css'
})
export class IngredientComponent implements OnInit {

  pack: any;
  selectedView: string = 'pack';
  newIngredient: any = { name: '', description: '', stock: 0 };
  ingredients: any[] = [];
  newItems: any[] = [];
  editPackData: any = {};
  editItems: any[] = [];
  ingredientData: any[] = [];
  newIngredientData: any = {
    Ingredients_name: '',
    Ingredients_des: '',
    Ingredients_image: '',
    main_stock: 0,
    sub_stock: 0,
    unit: 'ml'
  };
  editIngredientData: any = {};
  selectedStockField: string = 'main_stock';
  selectedImageFile: File | null = null;
  selectedEditImageFile: File | null = null;

  constructor(
    private service: IngredientService,
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadPackData();
    this.loadIngredients();
  }

  setView(view: string) {
    this.selectedView = view;
    if (view === 'pack') {
      this.loadPackData();
    } else if (view === 'main' || view === 'sub') {
      this.selectedStockField = view === 'main' ? 'main_stock' : 'sub_stock';
      this.loadIngredients();
    }
  }

  private loadPackData() {
    this.service.getAllPack().subscribe((res) => {
      this.pack = res;
      console.log('Pack:', this.pack);
    });
  }

  private loadIngredients() {
    this.service.getAllIngredient().subscribe((res) => {
        this.ingredients = res;
        console.log('Ingredients:', this.ingredients);
    });
  }

  addPack() {
    this.service.createIngredientPack(this.newIngredient).subscribe(
      (res: any) => {
        console.log("API Response:", res); 

        Swal.fire('สำเร็จ', 'เพิ่มข้อมูล Pack เรียบร้อย', 'success');
        this.loadPackData();
        this.newIngredient = { name: '', description: '', stock: 0 };

        if (res && res.id) {
          this.newItems = [{ ingredient_pack_id: res.id, ingredient_id: 0, qty: 1 }];
          console.log("🔹 Created Pack ID:", res.id);

          this.openAddItemModal();
        } else {
          console.error("Error: ingredient_pack_id is still null. API Response:", res);
        }
      },
      (error) => {
        console.error("Error creating pack:", error);
        Swal.fire('Error', 'เกิดข้อผิดพลาด', 'error');
      }
    );
  }

  openAddItemModal() {
    const addItemModalElement = document.getElementById('addItemModal');
    if (!addItemModalElement) {
      console.error("Error: Add Item Modal element not found!");
      return;
    }

    console.log("Opening Add Item Modal for ingredient_pack_id:", this.newItems[0].ingredient_pack_id);

    const addItemModal = new (window as any).bootstrap.Modal(addItemModalElement);
    addItemModal.show();
  }

  addItemRow() {
    if (!this.newItems[0]?.ingredient_pack_id) {
      console.error("Error: ingredient_pack_id is missing!");
      return;
    }

    this.newItems.push({ ingredient_pack_id: this.newItems[0].ingredient_pack_id, ingredient_id: 0, qty: 1 });
  }

  removeItem(index: number) {
    this.newItems.splice(index, 1);
  }

  async submitItems() {
    if (this.newItems.some(item => !item.ingredient_id || !item.qty)) {
        Swal.fire('Error', 'กรุณากรอกข้อมูลให้ครบถ้วน', 'error');
        return;
    }

    console.log("🔹 เริ่มส่งข้อมูล Item ทีละตัว...");
    
    for (const item of this.newItems) {
        try {
            console.log(JSON.stringify(item, null, 2));
            await this.service.createIngredientPackItem(item).toPromise();
            console.log("Item ส่งสำเร็จ:", item);
        } catch (error) {
            console.error("Error creating item:", error);
            Swal.fire('Error', 'เกิดข้อผิดพลาด', 'error');
            return;  
        }
    }

    Swal.fire('สำเร็จ', 'เพิ่ม Item ใน Pack เรียบร้อย!', 'success');
    this.newItems = [];
  }

  editPack(pack: any) {
    this.editPackData = { ...pack };
  
    this.service.getItemsByPackId(pack.id).subscribe({
      next: (items) => {
        this.editItems = items;
        this.openEditModal();
      },
      error: (err) => {
        console.warn("ไม่พบ Items หรือเกิดข้อผิดพลาด: ", err);
        this.editItems = []; 
        this.openEditModal();
      }
    });
  }  
  
  openEditModal() {
    const modalElement = document.getElementById('editPackModal');
    if (modalElement) {
      const modal = new (window as any).bootstrap.Modal(modalElement);
      modal.show();
    }
  }
  
  updatePack() {
    this.service.updatePack(this.editPackData.id, this.editPackData).subscribe(() => {
      Swal.fire('สำเร็จ', 'อัปเดตแพ็คเรียบร้อย', 'success');
      this.loadPackData();
    });
  }
  
  updateItem(item: any) {
    this.service.updateItem(item.id, item).subscribe(() => {
      Swal.fire('สำเร็จ', 'อัปเดตไอเทมเรียบร้อย', 'success');
    });
  }
  
  addNewEditItem() {
    this.editItems.push({
      ingredient_pack_id: this.editPackData.id,
      ingredient_id: 0,
      qty: 1
    });
  }
  
  submitNewItem(item: any) {
    this.service.createIngredientPackItem(item).subscribe(() => {
      Swal.fire('สำเร็จ', 'เพิ่มไอเทมเรียบร้อย', 'success');
    });
  }
  
  deletePackAndItems(packId: number) {
    Swal.fire({
      title: 'คุณแน่ใจหรือไม่?',
      text: 'การลบนี้จะลบทั้ง Pack และ Items ทั้งหมดที่เกี่ยวข้อง',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#6c757d',
      confirmButtonText: 'ใช่, ลบเลย',
      cancelButtonText: 'ยกเลิก'
    }).then((result) => {
      if (result.isConfirmed) {
        this.service.getItemsByPackId(packId).subscribe({
          next: (items) => {
            const deletePromises = items.map((item: any) =>
              this.service.deleteItem(item.id).toPromise()
            );
            Promise.all(deletePromises).then(() => {
              this.service.deletePack(packId).subscribe(() => {
                Swal.fire('สำเร็จ', 'ลบ Pack และไอเทมทั้งหมดแล้ว', 'success');
                this.loadPackData();
              });
            });
          },
          error: (err) => {
            console.warn("ไม่พบ Items หรือเกิดข้อผิดพลาด: ", err);
            this.service.deletePack(packId).subscribe(() => {
              Swal.fire('สำเร็จ', 'ลบ Pack เรียบร้อยแล้ว (ไม่มี Item)', 'success');
              this.loadPackData();
            });
          }
        });
      }
    });
  }  

  onImageSelected(event: any) {
    this.selectedImageFile = event.target.files[0];
  }
  
  onEditImageSelected(event: any) {
    this.selectedEditImageFile = event.target.files[0];
  }
  
  createIngredient() {
    const formData = new FormData();
    formData.append("Ingredients_name", this.newIngredientData.Ingredients_name);
    formData.append("Ingredients_des", this.newIngredientData.Ingredients_des);
    formData.append("main_stock", this.newIngredientData.main_stock.toString());
    formData.append("sub_stock", this.newIngredientData.sub_stock.toString());
    formData.append("unit", this.newIngredientData.unit);
  
    if (this.selectedImageFile) {
      formData.append("Ingredients_image", this.selectedImageFile);
    }
  
    this.service.createIngredient(formData).subscribe(() => {
      Swal.fire('สำเร็จ', 'เพิ่มวัตถุดิบแล้ว', 'success');
      this.loadIngredients();
      this.newIngredientData = { Ingredients_name: '', Ingredients_des: '', main_stock: 0, sub_stock: 0, unit: 'ml' };
      this.selectedImageFile = null;
    });
  }    
  
  editIngredient(ingredient: any) {
    this.editIngredientData = { ...ingredient };
    const modal = new (window as any).bootstrap.Modal(document.getElementById('editIngredientModal'));
    modal.show();
  }
  
  updateIngredient() {
    const formData = new FormData();
    formData.append("Ingredients_name", this.editIngredientData.Ingredients_name);
    formData.append("Ingredients_des", this.editIngredientData.Ingredients_des);
    formData.append("main_stock", this.editIngredientData.main_stock.toString());
    formData.append("sub_stock", this.editIngredientData.sub_stock.toString());
    formData.append("unit", this.editIngredientData.unit);
  
    if (this.selectedEditImageFile) {
      formData.append("Ingredients_image", this.selectedEditImageFile);
    }
  
    this.service.updateIngredient(this.editIngredientData.Ingredients_id, formData).subscribe(() => {
      Swal.fire('สำเร็จ', 'อัปเดตวัตถุดิบแล้ว', 'success');
      this.loadIngredients();
      this.selectedEditImageFile = null;
    });
  }    
  
  deleteIngredient(id: number) {
    Swal.fire({
      title: 'ยืนยันการลบ',
      text: 'คุณแน่ใจว่าต้องการลบวัตถุดิบนี้?',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'ใช่',
      cancelButtonText: 'ยกเลิก'
    }).then(result => {
      if (result.isConfirmed) {
        this.service.deleteIngredient(id).subscribe(() => {
          Swal.fire('ลบแล้ว', 'วัตถุดิบถูกลบเรียบร้อย', 'success');
          this.loadIngredients();
        });
      }
    });
  }
}
