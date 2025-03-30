import { TestBed } from '@angular/core/testing';

import { TestAIService } from './test-ai.service';

describe('TestAIService', () => {
  let service: TestAIService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TestAIService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
