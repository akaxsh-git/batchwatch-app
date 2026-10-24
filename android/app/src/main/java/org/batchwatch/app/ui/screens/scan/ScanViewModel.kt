package org.batchwatch.app.ui.screens.scan

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.batchwatch.app.data.repository.MedicineRepository
import org.batchwatch.app.data.repository.RepositoryProvider
import org.batchwatch.app.domain.model.ScanDraft
import org.batchwatch.app.domain.util.ImageCompressor

sealed interface ScanUiState {
    object Idle : ScanUiState
    object Processing : ScanUiState
    data class Success(val draft: ScanDraft) : ScanUiState
    data class Error(val message: String) : ScanUiState
}

class ScanViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: MedicineRepository = RepositoryProvider.getRepository(application)

    private val _uiState = MutableStateFlow<ScanUiState>(ScanUiState.Idle)
    val uiState: StateFlow<ScanUiState> = _uiState.asStateFlow()

    fun processImageUri(uri: Uri) {
        viewModelScope.launch {
            _uiState.value = ScanUiState.Processing
            try {
                val compressedBytes = ImageCompressor.compressUri(getApplication(), uri)
                val result = repository.scanImage(compressedBytes, uri.toString())
                result.fold(
                    onSuccess = { draft ->
                        _uiState.value = ScanUiState.Success(draft)
                    },
                    onFailure = { error ->
                        _uiState.value = ScanUiState.Error(error.message ?: "Failed to process photo")
                    }
                )
            } catch (e: Exception) {
                _uiState.value = ScanUiState.Error(e.message ?: "Failed to read image")
            }
        }
    }

    fun processCapturedBytes(bytes: ByteArray, photoUri: String? = null) {
        viewModelScope.launch {
            _uiState.value = ScanUiState.Processing
            try {
                val compressedBytes = ImageCompressor.compressBytes(bytes)
                val result = repository.scanImage(compressedBytes, photoUri)
                result.fold(
                    onSuccess = { draft ->
                        _uiState.value = ScanUiState.Success(draft)
                    },
                    onFailure = { error ->
                        _uiState.value = ScanUiState.Error(error.message ?: "Failed to process photo")
                    }
                )
            } catch (e: Exception) {
                _uiState.value = ScanUiState.Error(e.message ?: "Failed to process image bytes")
            }
        }
    }

    fun resetState() {
        _uiState.value = ScanUiState.Idle
    }
}
