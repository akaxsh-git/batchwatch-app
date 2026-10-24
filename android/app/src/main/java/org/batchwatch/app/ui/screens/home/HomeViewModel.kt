package org.batchwatch.app.ui.screens.home

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import org.batchwatch.app.data.repository.MedicineRepository
import org.batchwatch.app.data.repository.RepositoryProvider
import org.batchwatch.app.domain.model.Medicine

class HomeViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: MedicineRepository = RepositoryProvider.getRepository(application)

    val isDemoMode: Boolean = repository.isDemoMode

    val savedMedicines: StateFlow<List<Medicine>> = repository.getSavedMedicines()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
}
