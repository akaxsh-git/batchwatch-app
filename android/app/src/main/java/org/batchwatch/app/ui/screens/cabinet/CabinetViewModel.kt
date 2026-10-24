package org.batchwatch.app.ui.screens.cabinet

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.batchwatch.app.data.repository.MedicineRepository
import org.batchwatch.app.data.repository.RepositoryProvider
import org.batchwatch.app.domain.model.Medicine

class CabinetViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: MedicineRepository = RepositoryProvider.getRepository(application)

    val medicines: StateFlow<List<Medicine>> = repository.getSavedMedicines()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    fun deleteMedicine(id: Long) {
        viewModelScope.launch {
            repository.deleteMedicine(id)
        }
    }
}
