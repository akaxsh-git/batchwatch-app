package org.batchwatch.app.ui.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.launch
import org.batchwatch.app.data.local.UserPreferences
import org.batchwatch.app.data.repository.RepositoryProvider
import org.batchwatch.app.domain.model.CheckResult
import org.batchwatch.app.domain.model.ScanDraft
import org.batchwatch.app.ui.screens.cabinet.CabinetScreen
import org.batchwatch.app.ui.screens.confirm.ConfirmScreen
import org.batchwatch.app.ui.screens.home.HomeScreen
import org.batchwatch.app.ui.screens.onboarding.OnboardingScreen
import org.batchwatch.app.ui.screens.result.ResultScreen
import org.batchwatch.app.ui.screens.scan.ScanScreen
import org.batchwatch.app.ui.screens.search.ManualSearchScreen
import org.batchwatch.app.ui.screens.settings.SettingsScreen

sealed interface Screen {
    object Onboarding : Screen
    object Home : Screen
    object Scan : Screen
    data class Confirm(val draft: ScanDraft) : Screen
    data class Result(val result: CheckResult) : Screen
    object Cabinet : Screen
    object Search : Screen
    object Settings : Screen
}

@Composable
fun BatchWatchNavGraph(
    initialScreen: Screen,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val preferences = remember { UserPreferences.create(context) }

    val backStack = remember { mutableStateListOf<Screen>(initialScreen) }
    val currentScreen = backStack.lastOrNull() ?: Screen.Home

    BackHandler(enabled = backStack.size > 1) {
        backStack.removeAt(backStack.lastIndex)
    }

    fun navigateTo(screen: Screen) {
        backStack.add(screen)
    }

    fun popBack() {
        if (backStack.size > 1) {
            backStack.removeAt(backStack.lastIndex)
        }
    }

    fun navigateHomeClearingStack() {
        backStack.clear()
        backStack.add(Screen.Home)
    }

    AnimatedContent(
        targetState = currentScreen,
        transitionSpec = { fadeIn() togetherWith fadeOut() },
        label = "ScreenTransition",
        modifier = modifier
    ) { screen ->
        when (screen) {
            is Screen.Onboarding -> {
                OnboardingScreen(
                    onComplete = {
                        coroutineScope.launch {
                            preferences.setOnboardingCompleted(true)
                            navigateHomeClearingStack()
                        }
                    }
                )
            }

            is Screen.Home -> {
                HomeScreen(
                    onNavigateToScan = { navigateTo(Screen.Scan) },
                    onNavigateToSearch = { navigateTo(Screen.Search) },
                    onNavigateToCabinet = { navigateTo(Screen.Cabinet) },
                    onNavigateToSettings = { navigateTo(Screen.Settings) }
                )
            }

            is Screen.Scan -> {
                ScanScreen(
                    onScanSuccess = { draft ->
                        navigateTo(Screen.Confirm(draft))
                    },
                    onBack = { popBack() }
                )
            }

            is Screen.Confirm -> {
                ConfirmScreen(
                    draft = screen.draft,
                    onConfirm = { batch, product, manufacturer ->
                        coroutineScope.launch {
                            val repo = RepositoryProvider.getRepository(context)
                            val res = repo.checkBatch(batch, product, manufacturer)
                            res.onSuccess { checkResult ->
                                navigateTo(Screen.Result(checkResult))
                            }
                        }
                    },
                    onBack = { popBack() }
                )
            }

            is Screen.Result -> {
                ResultScreen(
                    result = screen.result,
                    onNavigateHome = { navigateHomeClearingStack() },
                    onBack = { popBack() }
                )
            }

            is Screen.Cabinet -> {
                CabinetScreen(
                    onBack = { popBack() }
                )
            }

            is Screen.Search -> {
                ManualSearchScreen(
                    onSearchResult = { checkResult ->
                        navigateTo(Screen.Result(checkResult))
                    },
                    onBack = { popBack() }
                )
            }

            is Screen.Settings -> {
                SettingsScreen(
                    onBack = { popBack() }
                )
            }
        }
    }
}
