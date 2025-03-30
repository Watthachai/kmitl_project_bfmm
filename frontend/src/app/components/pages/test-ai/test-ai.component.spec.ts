import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TestAIComponent } from './test-ai.component';

describe('TestAIComponent', () => {
  let component: TestAIComponent;
  let fixture: ComponentFixture<TestAIComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [TestAIComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TestAIComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
