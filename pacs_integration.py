# PACS (Picture Archiving and Communication System) Integration Module
# Supports integration with external PACS systems

import requests
import json
from typing import Dict, List, Optional

class PACSConnector:
    """Base class for PACS system integration"""
    
    def __init__(self, pacs_url: str, api_key: str = None, username: str = None, password: str = None):
        """
        Initialize PACS connector
        
        Args:
            pacs_url: URL of the PACS system
            api_key: API key for authentication (if applicable)
            username: Username for authentication
            password: Password for authentication
        """
        self.pacs_url = pacs_url
        self.api_key = api_key
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        elif username and password:
            self.session.auth = (username, password)
    
    def get_patient_studies(self, patient_id: str) -> List[Dict]:
        """Retrieve all studies for a patient from PACS"""
        try:
            endpoint = f"{self.pacs_url}/patients/{patient_id}/studies"
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error retrieving patient studies: {e}")
            return []
    
    def get_study_series(self, study_id: str) -> List[Dict]:
        """Retrieve all series in a study from PACS"""
        try:
            endpoint = f"{self.pacs_url}/studies/{study_id}/series"
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error retrieving study series: {e}")
            return []
    
    def get_series_instances(self, study_id: str, series_id: str) -> List[Dict]:
        """Retrieve all instances in a series from PACS"""
        try:
            endpoint = f"{self.pacs_url}/studies/{study_id}/series/{series_id}/instances"
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error retrieving series instances: {e}")
            return []
    
    def download_instance(self, study_id: str, series_id: str, instance_id: str, output_path: str) -> bool:
        """Download a DICOM instance from PACS"""
        try:
            endpoint = f"{self.pacs_url}/studies/{study_id}/series/{series_id}/instances/{instance_id}"
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error downloading instance: {e}")
            return False
    
    def upload_result(self, study_id: str, result_data: Dict) -> bool:
        """Upload analysis result back to PACS"""
        try:
            endpoint = f"{self.pacs_url}/studies/{study_id}/results"
            response = self.session.post(endpoint, json=result_data)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error uploading result: {e}")
            return False
    
    def create_patient_record(self, patient_data: Dict) -> Optional[str]:
        """Create a new patient record in PACS"""
        try:
            endpoint = f"{self.pacs_url}/patients"
            response = self.session.post(endpoint, json=patient_data)
            response.raise_for_status()
            result = response.json()
            return result.get('patient_id')
        except Exception as e:
            print(f"Error creating patient record: {e}")
            return None

class DicomWebConnector(PACSConnector):
    """DICOMweb standard connector for PACS systems"""
    
    def __init__(self, pacs_url: str, api_key: str = None, username: str = None, password: str = None):
        """Initialize DICOMweb connector"""
        super().__init__(pacs_url, api_key, username, password)
        self.session.headers.update({'Accept': 'application/dicom+json'})
    
    def search_for_patients(self, name: str = None, patient_id: str = None) -> List[Dict]:
        """Search for patients in PACS"""
        try:
            endpoint = f"{self.pacs_url}/qido-rs/studies"
            params = {}
            if name:
                params['PatientName'] = name
            if patient_id:
                params['PatientID'] = patient_id
            
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error searching patients: {e}")
            return []
    
    def retrieve_study_metadata(self, study_uid: str) -> Dict:
        """Retrieve metadata for a study using DICOMweb"""
        try:
            endpoint = f"{self.pacs_url}/wado-rs/studies/{study_uid}/metadata"
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error retrieving study metadata: {e}")
            return {}

class PACSConfig:
    """Configuration manager for PACS integration"""
    
    # Supported PACS systems
    SUPPORTED_SYSTEMS = {
        'dcm4chee': {
            'name': 'DCM4CHEE',
            'default_port': 8080,
            'api_path': '/dcm4chee-arc/aets'
        },
        'orthanc': {
            'name': 'Orthanc',
            'default_port': 8042,
            'api_path': '/api'
        },
        'conquestdicom': {
            'name': 'Conquest DICOM',
            'default_port': 1234,
            'api_path': ''
        },
    }
    
    @staticmethod
    def get_connector(pacs_system: str, pacs_url: str, api_key: str = None, 
                     username: str = None, password: str = None) -> Optional[PACSConnector]:
        """Get appropriate PACS connector based on system type"""
        if pacs_system == 'dicomweb':
            return DicomWebConnector(pacs_url, api_key, username, password)
        else:
            return PACSConnector(pacs_url, api_key, username, password)

def upload_scan_to_pacs(scan_path: str, patient_id: str, patient_name: str, pacs_connector: PACSConnector) -> bool:
    """
    Upload a scan to PACS system
    
    Args:
        scan_path: Path to the scan file
        patient_id: Patient ID
        patient_name: Patient name
        pacs_connector: PACS connector instance
    
    Returns:
        Success status
    """
    try:
        # Create patient record if needed
        patient_data = {
            'PatientID': patient_id,
            'PatientName': patient_name,
        }
        
        patient_created = pacs_connector.create_patient_record(patient_data)
        if not patient_created and patient_created is not None:
            patient_id = patient_created
        
        # For actual DICOM upload, you would need pydicom library
        # This is a placeholder for the integration
        print(f"Scan upload prepared for PACS: {scan_path}")
        return True
    except Exception as e:
        print(f"Error uploading scan to PACS: {e}")
        return False

def retrieve_pacs_studies(patient_id: str, pacs_connector: PACSConnector) -> List[Dict]:
    """Retrieve all studies for a patient from PACS"""
    try:
        return pacs_connector.get_patient_studies(patient_id)
    except Exception as e:
        print(f"Error retrieving PACS studies: {e}")
        return []

# Example usage:
# pacs = PACSConfig.get_connector('dicomweb', 'http://pacs-server:8080', api_key='your-api-key')
# studies = pacs.search_for_patients(patient_id='12345')
