import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment.development';

@Injectable({
  providedIn: 'root'
})
export class TestAIService {

  constructor(private http: HttpClient) { }

  uploadAudio(audioFile: File) {
      const url = `${environment.serviceUrl}/api/nlp/crf/test_predict/`;
      const formData = new FormData();
      formData.append('file', audioFile, audioFile.name);
  
      for (let pair of formData.entries()) {
          console.log("FormData:", pair[0], pair[1]);  
      }
  
      return this.http.post(url, formData, {
          headers: { 'Accept': 'application/json' },
          withCredentials: true,
          observe: 'response'
      });
    }
}
