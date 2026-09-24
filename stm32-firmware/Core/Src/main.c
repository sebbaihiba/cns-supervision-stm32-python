/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <string.h>
#include <stdio.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
typedef struct
{
  GPIO_TypeDef *port;
  uint16_t pin;
  const char *button_name;
} ButtonDebug_t;

typedef enum
{
  CNS_STATE_NORMAL = 0U,
  CNS_STATE_WARNING,
  CNS_STATE_ALARME,
  CNS_STATE_HORS_SERVICE,
  CNS_STATE_COUNT
} CnsState_t;

typedef enum
{
  CNS_FAULT_OK = 0U,
  CNS_FAULT_FONCTION_PERDUE,
  CNS_FAULT_SIGNAL_PERDU,
  CNS_FAULT_TEMPERATURE_ELEVEE,
  CNS_FAULT_ALIMENTATION_COUPEE,
  CNS_FAULT_COUNT
} CnsFault_t;

typedef enum
{
  OND_FAULT_OK = 0U,
  OND_FAULT_SECTEUR_COUPE,
  OND_FAULT_BATTERIE_FAIBLE,
  OND_FAULT_ONDULEUR_HS,
  OND_FAULT_COUNT
} OnduleurFault_t;

typedef struct
{
  uint8_t index;
  CnsFault_t cns_fault;
  OnduleurFault_t onduleur_fault;
  uint8_t alarm_after_delay;
} AutoScenarioEvent_t;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* =========================
 * Protocole binaire CNSP v1
 * Trame : START | VERSION | ADRESSE | DEFAUT | ETAT | COMPTEUR | CHECKSUM
 * ========================= */
#define CNSP_START_BYTE                  0xAAU
#define CNSP_VERSION                     0x01U
#define CNSP_FRAME_SIZE                  7U

/* Adresses systemes */
#define CNSP_ADDR_DME                    0x01U
#define CNSP_ADDR_ILS_LOCALIZER          0x02U
#define CNSP_ADDR_GLIDE_SLOPE            0x03U
#define CNSP_ADDR_VHF                    0x04U
#define CNSP_ADDR_ADS_B                  0x05U
#define CNSP_ADDR_ONDULEUR               0x06U

/* Codes defauts CNS */
#define CNSP_FAULT_OK                    0x00U
#define CNSP_FAULT_FONCTION_PERDUE       0x01U
#define CNSP_FAULT_SIGNAL_PERDU          0x02U
#define CNSP_FAULT_TEMPERATURE_ELEVEE    0x03U
#define CNSP_FAULT_ALIMENTATION_COUPEE   0x04U

/* Codes defauts energie / onduleur */
#define CNSP_FAULT_SECTEUR_COUPE         0x10U
#define CNSP_FAULT_BATTERIE_FAIBLE       0x11U
#define CNSP_FAULT_ONDULEUR_HS           0x12U
#define CNSP_FAULT_ALIMENTATION_CNS      0x13U

/* Codes etats */
#define CNSP_STATE_NORMAL                0x00U
#define CNSP_STATE_WARNING               0x01U
#define CNSP_STATE_ALARME                0x02U
#define CNSP_STATE_HORS_SERVICE          0x03U


/*
 * CNS_UART_DEBUG_MODE :
 * 0U : aucun affichage UART
 * 1U : à chaque appui, affiche :
 *      CNS;DME;WARNING
 *      CNS_ALL;DME=WARNING;ILS_LOCALIZER=NORMAL;...
 * 2U : affichage périodique de tous les états CNS
 */
#define CNS_UART_DEBUG_MODE             1U

/*
 * Fréquence d'affichage pour le mode 2.
 * Exemple :
 * 1U  => 1 affichage par seconde
 * 2U  => 2 affichages par seconde
 * 5U  => 5 affichages par seconde
 */
#define CNS_STATE_PRINT_FREQ_HZ         1U

#define BUTTON_DEBOUNCE_MS              30U
#define DEBUG_UART                      (&huart1)
#define DEBUG_UART_TIMEOUT_MS           100U
#define BUTTON_COUNT                    6U
#define CNS_SYSTEM_COUNT                5U
#define ONDULEUR_INDEX                  5U
#define CNS_ALARM_DELAY_MS              5000U

/*
 * AUTO_SCENARIO_ENABLE :
 * 1U : la STM32 genere automatiquement les defauts et envoie les trames CNSP.
 * 0U : les boutons restent actifs pour les tests manuels.
 */
#define AUTO_SCENARIO_ENABLE            1U
#define AUTO_SCENARIO_PERIOD_MS         5000U

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
DFSDM_Channel_HandleTypeDef hdfsdm1_channel1;

I2C_HandleTypeDef hi2c2;

QSPI_HandleTypeDef hqspi;

SPI_HandleTypeDef hspi3;

UART_HandleTypeDef huart1;
UART_HandleTypeDef huart3;

PCD_HandleTypeDef hpcd_USB_OTG_FS;

/* USER CODE BEGIN PV */

static const ButtonDebug_t g_buttons[BUTTON_COUNT] =
{
  {Bouton1_GPIO_Port, Bouton1_Pin, "B1"},
  {Bouton2_GPIO_Port, Bouton2_Pin, "B2"},
  {Bouton3_GPIO_Port, Bouton3_Pin, "B3"},
  {Bouton4_GPIO_Port, Bouton4_Pin, "B4"},
  {Bouton5_GPIO_Port, Bouton5_Pin, "B5"},
  {Bouton6_GPIO_Port, Bouton6_Pin, "B6"}
};

static const char *g_cns_system_names[BUTTON_COUNT] =
{
  "DME",
  "ILS_LOCALIZER",
  "GLIDE_SLOPE",
  "VHF",
  "ADS_B",
  "ONDULEUR"
};

static const char *g_cns_state_names[CNS_STATE_COUNT] =
{
  "NORMAL",
  "WARNING",
  "ALARME",
  "HORS_SERVICE"
};

static const char *g_cns_fault_names[CNS_FAULT_COUNT] =
{
  "OK",
  "FONCTION_PERDUE",
  "SIGNAL_PERDU",
  "TEMPERATURE_ELEVEE",
  "ALIMENTATION_COUPEE"
};

static const char *g_onduleur_fault_names[OND_FAULT_COUNT] =
{
  "OK",
  "SECTEUR_COUPE",
  "BATTERIE_FAIBLE",
  "ONDULEUR_HS"
};

static volatile uint8_t g_button_event_pending[BUTTON_COUNT] = {0};
static volatile uint32_t g_button_last_irq_tick[BUTTON_COUNT] = {0};

static CnsFault_t g_cns_faults[BUTTON_COUNT] =
{
  CNS_FAULT_OK,
  CNS_FAULT_OK,
  CNS_FAULT_OK,
  CNS_FAULT_OK,
  CNS_FAULT_OK,
  CNS_FAULT_OK
};

static OnduleurFault_t g_onduleur_fault = OND_FAULT_OK;

static CnsState_t g_cns_states[BUTTON_COUNT] =
{
  CNS_STATE_NORMAL,
  CNS_STATE_NORMAL,
  CNS_STATE_NORMAL,
  CNS_STATE_NORMAL,
  CNS_STATE_NORMAL,
  CNS_STATE_NORMAL
};

static uint32_t g_fault_start_tick[BUTTON_COUNT] = {0U};
static uint32_t g_last_state_print_tick = 0U;
static uint8_t g_cnsp_counter = 0U;
static uint32_t g_auto_scenario_last_tick = 0U;
static uint8_t g_auto_scenario_step = 0U;

/*
 * Scenario automatique de demonstration.
 * Les boutons ne sont plus necessaires en mode AUTO_SCENARIO_ENABLE = 1U.
 * Chaque ligne simule un etat envoye par un equipement CNS via le protocole CNSP v1.
 */
static const AutoScenarioEvent_t g_auto_scenario[] =
{
  /* DME */
  {0U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 0U},
  {0U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 1U},
  {0U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 0U},
  {0U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 1U},
  {0U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 0U},
  {0U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 1U},
  {0U, CNS_FAULT_ALIMENTATION_COUPEE,OND_FAULT_OK, 0U},
  {0U, CNS_FAULT_OK,                 OND_FAULT_OK, 0U},

  /* ILS LOCALIZER */
  {1U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 0U},
  {1U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 1U},
  {1U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 0U},
  {1U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 1U},
  {1U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 0U},
  {1U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 1U},
  {1U, CNS_FAULT_ALIMENTATION_COUPEE,OND_FAULT_OK, 0U},
  {1U, CNS_FAULT_OK,                 OND_FAULT_OK, 0U},

  /* GLIDE SLOPE */
  {2U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 0U},
  {2U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 1U},
  {2U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 0U},
  {2U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 1U},
  {2U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 0U},
  {2U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 1U},
  {2U, CNS_FAULT_ALIMENTATION_COUPEE,OND_FAULT_OK, 0U},
  {2U, CNS_FAULT_OK,                 OND_FAULT_OK, 0U},

  /* VHF */
  {3U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 0U},
  {3U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 1U},
  {3U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 0U},
  {3U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 1U},
  {3U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 0U},
  {3U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 1U},
  {3U, CNS_FAULT_ALIMENTATION_COUPEE,OND_FAULT_OK, 0U},
  {3U, CNS_FAULT_OK,                 OND_FAULT_OK, 0U},

  /* ADS-B */
  {4U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 0U},
  {4U, CNS_FAULT_FONCTION_PERDUE,    OND_FAULT_OK, 1U},
  {4U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 0U},
  {4U, CNS_FAULT_SIGNAL_PERDU,       OND_FAULT_OK, 1U},
  {4U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 0U},
  {4U, CNS_FAULT_TEMPERATURE_ELEVEE, OND_FAULT_OK, 1U},
  {4U, CNS_FAULT_ALIMENTATION_COUPEE,OND_FAULT_OK, 0U},
  {4U, CNS_FAULT_OK,                 OND_FAULT_OK, 0U},

  /* ONDULEUR */
  {ONDULEUR_INDEX, CNS_FAULT_OK, OND_FAULT_SECTEUR_COUPE,   0U},
  {ONDULEUR_INDEX, CNS_FAULT_OK, OND_FAULT_BATTERIE_FAIBLE, 0U},
  {ONDULEUR_INDEX, CNS_FAULT_OK, OND_FAULT_ONDULEUR_HS,     0U},
  {ONDULEUR_INDEX, CNS_FAULT_OK, OND_FAULT_OK,              0U}
};

#define AUTO_SCENARIO_COUNT ((uint8_t)(sizeof(g_auto_scenario) / sizeof(g_auto_scenario[0])))

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DFSDM1_Init(void);
static void MX_I2C2_Init(void);
static void MX_QUADSPI_Init(void);
static void MX_SPI3_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART3_UART_Init(void);
static void MX_USB_OTG_FS_PCD_Init(void);
/* USER CODE BEGIN PFP */

static void UART_SendString(const char *text);
static int8_t Button_GetIndexFromPin(uint16_t GPIO_Pin);
static uint8_t Button_IsPressed(uint8_t index);
static void Cns_GoToNextFault(uint8_t index);
static void Onduleur_GoToNextFault(void);
static CnsState_t Onduleur_DecideState(void);
static CnsState_t Cns_DecideState(uint8_t index);
static uint8_t Cns_AnySystemPowerFault(void);
static void Cns_DecisionTask(void);
static uint32_t Cns_GetStatePrintPeriodMs(void);
static void Cns_UART_EventTask(void);
static void Cns_UART_AllStatesTask(void);
static void Cns_UART_SendAllStates(void);
static void Cns_UART_SendEvent(uint8_t index);
static void Cns_UART_SendDiag(uint8_t index);
static uint8_t CNSP_GetAddress(uint8_t index);
static uint8_t CNSP_GetStateCode(CnsState_t state);
static uint8_t CNSP_GetFaultCode(uint8_t index);
static uint8_t CNSP_ComputeChecksum(const uint8_t *frame);
static void CNSP_SendFrame(uint8_t index);
static void AutoScenario_ApplyEvent(const AutoScenarioEvent_t *event);
static void AutoScenario_Task(void);

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

static void UART_SendString(const char *text)
{
  if (text == NULL)
  {
    return;
  }

  HAL_UART_Transmit(DEBUG_UART,
                    (uint8_t *)text,
                    (uint16_t)strlen(text),
                    DEBUG_UART_TIMEOUT_MS);
}

static uint8_t CNSP_GetAddress(uint8_t index)
{
  switch (index)
  {
    case 0U: return CNSP_ADDR_DME;
    case 1U: return CNSP_ADDR_ILS_LOCALIZER;
    case 2U: return CNSP_ADDR_GLIDE_SLOPE;
    case 3U: return CNSP_ADDR_VHF;
    case 4U: return CNSP_ADDR_ADS_B;
    case 5U: return CNSP_ADDR_ONDULEUR;
    default: return 0x00U;
  }
}

static uint8_t CNSP_GetStateCode(CnsState_t state)
{
  switch (state)
  {
    case CNS_STATE_NORMAL:       return CNSP_STATE_NORMAL;
    case CNS_STATE_WARNING:      return CNSP_STATE_WARNING;
    case CNS_STATE_ALARME:       return CNSP_STATE_ALARME;
    case CNS_STATE_HORS_SERVICE: return CNSP_STATE_HORS_SERVICE;
    default:                     return CNSP_STATE_NORMAL;
  }
}

static uint8_t CNSP_GetFaultCode(uint8_t index)
{
  if (index >= BUTTON_COUNT)
  {
    return CNSP_FAULT_OK;
  }

  if (index == ONDULEUR_INDEX)
  {
    if ((g_onduleur_fault == OND_FAULT_OK) && (Cns_AnySystemPowerFault() != 0U))
    {
      return CNSP_FAULT_ALIMENTATION_CNS;
    }

    switch (g_onduleur_fault)
    {
      case OND_FAULT_OK:              return CNSP_FAULT_OK;
      case OND_FAULT_SECTEUR_COUPE:   return CNSP_FAULT_SECTEUR_COUPE;
      case OND_FAULT_BATTERIE_FAIBLE: return CNSP_FAULT_BATTERIE_FAIBLE;
      case OND_FAULT_ONDULEUR_HS:     return CNSP_FAULT_ONDULEUR_HS;
      default:                        return CNSP_FAULT_OK;
    }
  }

  switch (g_cns_faults[index])
  {
    case CNS_FAULT_OK:                  return CNSP_FAULT_OK;
    case CNS_FAULT_FONCTION_PERDUE:     return CNSP_FAULT_FONCTION_PERDUE;
    case CNS_FAULT_SIGNAL_PERDU:        return CNSP_FAULT_SIGNAL_PERDU;
    case CNS_FAULT_TEMPERATURE_ELEVEE:  return CNSP_FAULT_TEMPERATURE_ELEVEE;
    case CNS_FAULT_ALIMENTATION_COUPEE: return CNSP_FAULT_ALIMENTATION_COUPEE;
    default:                            return CNSP_FAULT_OK;
  }
}

static uint8_t CNSP_ComputeChecksum(const uint8_t *frame)
{
  uint16_t sum = 0U;

  for (uint8_t i = 0U; i < (CNSP_FRAME_SIZE - 1U); i++)
  {
    sum = (uint16_t)(sum + frame[i]);
  }

  return (uint8_t)(sum & 0xFFU);
}

static void CNSP_SendFrame(uint8_t index)
{
  if (index >= BUTTON_COUNT)
  {
    return;
  }

  uint8_t frame[CNSP_FRAME_SIZE];

  frame[0] = CNSP_START_BYTE;
  frame[1] = CNSP_VERSION;
  frame[2] = CNSP_GetAddress(index);
  frame[3] = CNSP_GetFaultCode(index);
  frame[4] = CNSP_GetStateCode(g_cns_states[index]);
  frame[5] = g_cnsp_counter++;
  frame[6] = CNSP_ComputeChecksum(frame);

  HAL_UART_Transmit(DEBUG_UART, frame, CNSP_FRAME_SIZE, DEBUG_UART_TIMEOUT_MS);
}

static int8_t Button_GetIndexFromPin(uint16_t GPIO_Pin)
{
  for (uint8_t i = 0U; i < BUTTON_COUNT; i++)
  {
    if (GPIO_Pin == g_buttons[i].pin)
    {
      return (int8_t)i;
    }
  }

  return -1;
}

static uint8_t Button_IsPressed(uint8_t index)
{
  if (index >= BUTTON_COUNT)
  {
    return 0U;
  }

  /*
   * Bouton câblé entre GPIO et GND avec pull-up :
   * relâché = GPIO_PIN_SET
   * appuyé  = GPIO_PIN_RESET
   */
  if (HAL_GPIO_ReadPin(g_buttons[index].port, g_buttons[index].pin) == GPIO_PIN_RESET)
  {
    return 1U;
  }

  return 0U;
}

static void Cns_GoToNextFault(uint8_t index)
{
  if (index >= BUTTON_COUNT)
  {
    return;
  }

  /*
   * B6 represente l'ONDULEUR et simule des defauts energie.
   * Il n'utilise pas les memes defauts que les systemes CNS.
   */
  if (index == ONDULEUR_INDEX)
  {
    Onduleur_GoToNextFault();
    return;
  }

  g_cns_faults[index] = (CnsFault_t)(((uint32_t)g_cns_faults[index] + 1U) % CNS_FAULT_COUNT);
  g_fault_start_tick[index] = HAL_GetTick();
  g_cns_states[index] = Cns_DecideState(index);
}

static void Onduleur_GoToNextFault(void)
{
  g_onduleur_fault = (OnduleurFault_t)(((uint32_t)g_onduleur_fault + 1U) % OND_FAULT_COUNT);
  g_fault_start_tick[ONDULEUR_INDEX] = HAL_GetTick();
  g_cns_states[ONDULEUR_INDEX] = Onduleur_DecideState();
}

static CnsState_t Onduleur_DecideState(void)
{
  /*
   * L'onduleur est un systeme support energie.
   * - SECTEUR_COUPE : les systemes restent alimentes par batterie -> WARNING
   * - BATTERIE_FAIBLE : risque de perte d'alimentation -> ALARME
   * - ONDULEUR_HS : plus de support energie -> HORS_SERVICE
   * - Si un systeme CNS signale ALIMENTATION_COUPEE, l'onduleur passe ALARME.
   */
  if (g_onduleur_fault == OND_FAULT_ONDULEUR_HS)
  {
    return CNS_STATE_HORS_SERVICE;
  }

  if (g_onduleur_fault == OND_FAULT_BATTERIE_FAIBLE)
  {
    return CNS_STATE_ALARME;
  }

  if (g_onduleur_fault == OND_FAULT_SECTEUR_COUPE)
  {
    return CNS_STATE_WARNING;
  }

  if (Cns_AnySystemPowerFault() != 0U)
  {
    return CNS_STATE_ALARME;
  }

  return CNS_STATE_NORMAL;
}

static uint8_t Cns_AnySystemPowerFault(void)
{
  /*
   * Les 5 premiers elements sont les systemes CNS :
   * DME, ILS_LOCALIZER, GLIDE_SLOPE, VHF, ADS_B.
   *
   * Si l'un de ces systemes a un defaut ALIMENTATION_COUPEE,
   * l'onduleur doit passer en ALARME car il assure l'alimentation
   * de plusieurs systemes.
   */
  for (uint8_t i = 0U; i < CNS_SYSTEM_COUNT; i++)
  {
    if (g_cns_faults[i] == CNS_FAULT_ALIMENTATION_COUPEE)
    {
      return 1U;
    }
  }

  return 0U;
}

static CnsState_t Cns_DecideState(uint8_t index)
{
  if (index >= BUTTON_COUNT)
  {
    return CNS_STATE_NORMAL;
  }

  if (index == ONDULEUR_INDEX)
  {
    return Onduleur_DecideState();
  }

  /*
   * Si l'onduleur est totalement HS, les systemes alimentes par lui
   * deviennent hors service.
   */
  if (g_onduleur_fault == OND_FAULT_ONDULEUR_HS)
  {
    return CNS_STATE_HORS_SERVICE;
  }

  CnsFault_t fault = g_cns_faults[index];

  if (fault == CNS_FAULT_OK)
  {
    return CNS_STATE_NORMAL;
  }

  if (fault == CNS_FAULT_ALIMENTATION_COUPEE)
  {
    return CNS_STATE_HORS_SERVICE;
  }

  if ((HAL_GetTick() - g_fault_start_tick[index]) >= CNS_ALARM_DELAY_MS)
  {
    return CNS_STATE_ALARME;
  }

  return CNS_STATE_WARNING;
}

static void Cns_DecisionTask(void)
{
  /*
   * Machine d'etats embarquee :
   * - 5 systemes CNS : OK -> NORMAL
   * - 5 systemes CNS : ALIMENTATION_COUPEE -> HORS_SERVICE
   * - autres defauts -> WARNING puis ALARME apres CNS_ALARM_DELAY_MS
   * - ONDULEUR : support energie, passe en ALARME si un systeme CNS
   *   signale ALIMENTATION_COUPEE
   */
  for (uint8_t i = 0U; i < BUTTON_COUNT; i++)
  {
    CnsState_t new_state = Cns_DecideState(i);

    if (new_state != g_cns_states[i])
    {
      g_cns_states[i] = new_state;

      if (CNS_UART_DEBUG_MODE == 1U)
      {
        Cns_UART_SendEvent(i);
        Cns_UART_SendDiag(i);
        Cns_UART_SendAllStates();
      }
    }
  }
}

static uint32_t Cns_GetStatePrintPeriodMs(void)
{
  uint32_t freq_hz = CNS_STATE_PRINT_FREQ_HZ;

  if (freq_hz == 0U)
  {
    return 1000U;
  }

  uint32_t period_ms = 1000U / freq_hz;

  if (period_ms == 0U)
  {
    period_ms = 1U;
  }

  return period_ms;
}

static void Cns_UART_SendAllStates(void)
{
  /*
   * Vue globale CNSP : on envoie une trame binaire pour chaque systeme.
   */
  for (uint8_t i = 0U; i < BUTTON_COUNT; i++)
  {
    CNSP_SendFrame(i);
  }
}


static void Cns_UART_SendEvent(uint8_t index)
{
  /*
   * En CNSP, l'evenement est transporte par la meme trame binaire
   * que le diagnostic : adresse + defaut + etat.
   */
  CNSP_SendFrame(index);
}


static void Cns_UART_SendDiag(uint8_t index)
{
  /*
   * Diagnostic CNSP v1 : START | VERSION | ADRESSE | DEFAUT | ETAT | COMPTEUR | CHECKSUM
   */
  CNSP_SendFrame(index);
}


static void AutoScenario_ApplyEvent(const AutoScenarioEvent_t *event)
{
  if (event == NULL)
  {
    return;
  }

  uint32_t now = HAL_GetTick();
  uint8_t index = event->index;

  if (index >= BUTTON_COUNT)
  {
    return;
  }

  if (index == ONDULEUR_INDEX)
  {
    g_onduleur_fault = event->onduleur_fault;
    g_fault_start_tick[ONDULEUR_INDEX] = now;
    g_cns_states[ONDULEUR_INDEX] = Onduleur_DecideState();
  }
  else
  {
    g_cns_faults[index] = event->cns_fault;

    if ((event->alarm_after_delay != 0U) &&
        (event->cns_fault != CNS_FAULT_OK) &&
        (event->cns_fault != CNS_FAULT_ALIMENTATION_COUPEE))
    {
      g_fault_start_tick[index] = now - CNS_ALARM_DELAY_MS;
    }
    else
    {
      g_fault_start_tick[index] = now;
    }

    g_cns_states[index] = Cns_DecideState(index);

    /* L'etat de l'onduleur peut dependre d'un defaut alimentation d'un systeme CNS. */
    g_cns_states[ONDULEUR_INDEX] = Onduleur_DecideState();
  }

  /* En demonstration, on envoie la vue complete apres chaque evenement. */
  Cns_UART_SendAllStates();
}

static void AutoScenario_Task(void)
{
#if (AUTO_SCENARIO_ENABLE == 1U)
  uint32_t now = HAL_GetTick();

  if ((now - g_auto_scenario_last_tick) < AUTO_SCENARIO_PERIOD_MS)
  {
    return;
  }

  g_auto_scenario_last_tick = now;

  AutoScenario_ApplyEvent(&g_auto_scenario[g_auto_scenario_step]);

  g_auto_scenario_step++;
  if (g_auto_scenario_step >= AUTO_SCENARIO_COUNT)
  {
    g_auto_scenario_step = 0U;
  }
#endif
}

static void Cns_UART_EventTask(void)
{
  if (CNS_UART_DEBUG_MODE != 1U)
  {
    return;
  }

  for (uint8_t i = 0U; i < BUTTON_COUNT; i++)
  {
    uint8_t pending = 0U;

    __disable_irq();
    pending = g_button_event_pending[i];
    g_button_event_pending[i] = 0U;
    __enable_irq();

    if (pending != 0U)
    {
      Cns_GoToNextFault(i);

      Cns_UART_SendEvent(i);
      Cns_UART_SendDiag(i);
      Cns_UART_SendAllStates();
    }
  }
}

static void Cns_UART_AllStatesTask(void)
{
  if (CNS_UART_DEBUG_MODE != 2U)
  {
    return;
  }

  uint32_t now = HAL_GetTick();
  uint32_t period_ms = Cns_GetStatePrintPeriodMs();

  if ((now - g_last_state_print_tick) < period_ms)
  {
    return;
  }

  g_last_state_print_tick = now;

  Cns_UART_SendAllStates();
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  MX_GPIO_Init();
  MX_DFSDM1_Init();
  MX_I2C2_Init();
  MX_QUADSPI_Init();
  MX_SPI3_Init();
  MX_USART1_UART_Init();
  MX_USART3_UART_Init();
  MX_USB_OTG_FS_PCD_Init();

  /* USER CODE BEGIN 2 */
  /*
   * Version V2 : protocole binaire CNSP v1.
   * La STM32 n'envoie plus de texte ASCII.
   * Elle envoie des trames de 7 octets :
   * AA | 01 | ADRESSE | DEFAUT | ETAT | COMPTEUR | CHECKSUM
   */
  Cns_UART_SendAllStates();
  /* USER CODE END 2 */

  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
#if (AUTO_SCENARIO_ENABLE == 1U)
    AutoScenario_Task();
#else
    Cns_UART_EventTask();
#endif
    Cns_DecisionTask();
    Cns_UART_AllStatesTask();
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  if (HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) != HAL_OK)
  {
    Error_Handler();
  }

  HAL_PWR_EnableBkUpAccess();
  __HAL_RCC_LSEDRIVE_CONFIG(RCC_LSEDRIVE_LOW);

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_LSE|RCC_OSCILLATORTYPE_MSI;
  RCC_OscInitStruct.LSEState = RCC_LSE_ON;
  RCC_OscInitStruct.MSIState = RCC_MSI_ON;
  RCC_OscInitStruct.MSICalibrationValue = 0;
  RCC_OscInitStruct.MSIClockRange = RCC_MSIRANGE_6;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_MSI;
  RCC_OscInitStruct.PLL.PLLM = 1;
  RCC_OscInitStruct.PLL.PLLN = 40;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
  RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
  RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;

  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK)
  {
    Error_Handler();
  }

  HAL_RCCEx_EnableMSIPLLMode();
}

/**
  * @brief DFSDM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_DFSDM1_Init(void)
{
  hdfsdm1_channel1.Instance = DFSDM1_Channel1;
  hdfsdm1_channel1.Init.OutputClock.Activation = ENABLE;
  hdfsdm1_channel1.Init.OutputClock.Selection = DFSDM_CHANNEL_OUTPUT_CLOCK_SYSTEM;
  hdfsdm1_channel1.Init.OutputClock.Divider = 2;
  hdfsdm1_channel1.Init.Input.Multiplexer = DFSDM_CHANNEL_EXTERNAL_INPUTS;
  hdfsdm1_channel1.Init.Input.DataPacking = DFSDM_CHANNEL_STANDARD_MODE;
  hdfsdm1_channel1.Init.Input.Pins = DFSDM_CHANNEL_FOLLOWING_CHANNEL_PINS;
  hdfsdm1_channel1.Init.SerialInterface.Type = DFSDM_CHANNEL_SPI_RISING;
  hdfsdm1_channel1.Init.SerialInterface.SpiClock = DFSDM_CHANNEL_SPI_CLOCK_INTERNAL;
  hdfsdm1_channel1.Init.Awd.FilterOrder = DFSDM_CHANNEL_FASTSINC_ORDER;
  hdfsdm1_channel1.Init.Awd.Oversampling = 1;
  hdfsdm1_channel1.Init.Offset = 0;
  hdfsdm1_channel1.Init.RightBitShift = 0x00;

  if (HAL_DFSDM_ChannelInit(&hdfsdm1_channel1) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C2_Init(void)
{
  hi2c2.Instance = I2C2;
  hi2c2.Init.Timing = 0x00000E14;
  hi2c2.Init.OwnAddress1 = 0;
  hi2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c2.Init.OwnAddress2 = 0;
  hi2c2.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_I2C_Init(&hi2c2) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_I2CEx_ConfigAnalogFilter(&hi2c2, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_I2CEx_ConfigDigitalFilter(&hi2c2, 0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief QUADSPI Initialization Function
  * @param None
  * @retval None
  */
static void MX_QUADSPI_Init(void)
{
  hqspi.Instance = QUADSPI;
  hqspi.Init.ClockPrescaler = 2;
  hqspi.Init.FifoThreshold = 4;
  hqspi.Init.SampleShifting = QSPI_SAMPLE_SHIFTING_HALFCYCLE;
  hqspi.Init.FlashSize = 23;
  hqspi.Init.ChipSelectHighTime = QSPI_CS_HIGH_TIME_1_CYCLE;
  hqspi.Init.ClockMode = QSPI_CLOCK_MODE_0;

  if (HAL_QSPI_Init(&hqspi) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief SPI3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_SPI3_Init(void)
{
  hspi3.Instance = SPI3;
  hspi3.Init.Mode = SPI_MODE_MASTER;
  hspi3.Init.Direction = SPI_DIRECTION_2LINES;
  hspi3.Init.DataSize = SPI_DATASIZE_4BIT;
  hspi3.Init.CLKPolarity = SPI_POLARITY_LOW;
  hspi3.Init.CLKPhase = SPI_PHASE_1EDGE;
  hspi3.Init.NSS = SPI_NSS_SOFT;
  hspi3.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
  hspi3.Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi3.Init.TIMode = SPI_TIMODE_DISABLE;
  hspi3.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi3.Init.CRCPolynomial = 7;
  hspi3.Init.CRCLength = SPI_CRC_LENGTH_DATASIZE;
  hspi3.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;

  if (HAL_SPI_Init(&hspi3) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;

  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART3_UART_Init(void)
{
  huart3.Instance = USART3;
  huart3.Init.BaudRate = 115200;
  huart3.Init.WordLength = UART_WORDLENGTH_8B;
  huart3.Init.StopBits = UART_STOPBITS_1;
  huart3.Init.Parity = UART_PARITY_NONE;
  huart3.Init.Mode = UART_MODE_TX_RX;
  huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart3.Init.OverSampling = UART_OVERSAMPLING_16;
  huart3.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart3.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;

  if (HAL_UART_Init(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USB_OTG_FS Initialization Function
  * @param None
  * @retval None
  */
static void MX_USB_OTG_FS_PCD_Init(void)
{
  hpcd_USB_OTG_FS.Instance = USB_OTG_FS;
  hpcd_USB_OTG_FS.Init.dev_endpoints = 6;
  hpcd_USB_OTG_FS.Init.speed = PCD_SPEED_FULL;
  hpcd_USB_OTG_FS.Init.phy_itface = PCD_PHY_EMBEDDED;
  hpcd_USB_OTG_FS.Init.Sof_enable = DISABLE;
  hpcd_USB_OTG_FS.Init.low_power_enable = DISABLE;
  hpcd_USB_OTG_FS.Init.lpm_enable = DISABLE;
  hpcd_USB_OTG_FS.Init.battery_charging_enable = DISABLE;
  hpcd_USB_OTG_FS.Init.use_dedicated_ep1 = DISABLE;
  hpcd_USB_OTG_FS.Init.vbus_sensing_enable = DISABLE;

  if (HAL_PCD_Init(&hpcd_USB_OTG_FS) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOE, M24SR64_Y_RF_DISABLE_Pin|M24SR64_Y_GPO_Pin|ISM43362_RST_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, ARD_D10_Pin|SPBTLE_RF_RST_Pin|ARD_D9_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, ISM43362_BOOT0_Pin|ISM43362_WAKEUP_Pin|LED2_Pin|SPSGRF_915_SDN_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOD, USB_OTG_FS_PWR_EN_Pin|PMOD_RESET_Pin|STSAFE_A100_RESET_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(SPBTLE_RF_SPI3_CSN_GPIO_Port, SPBTLE_RF_SPI3_CSN_Pin, GPIO_PIN_SET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOC, VL53L0X_XSHUT_Pin|LED3_WIFI__LED4_BLE_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(SPSGRF_915_SPI3_CSN_GPIO_Port, SPSGRF_915_SPI3_CSN_Pin, GPIO_PIN_SET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(ISM43362_SPI3_CSN_GPIO_Port, ISM43362_SPI3_CSN_Pin, GPIO_PIN_SET);

  GPIO_InitStruct.Pin = M24SR64_Y_RF_DISABLE_Pin|M24SR64_Y_GPO_Pin|ISM43362_RST_Pin|ISM43362_SPI3_CSN_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = SPSGRF_915_GPIO3_EXTI5_Pin|SPBTLE_RF_IRQ_EXTI6_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = BUTTON_EXTI13_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(BUTTON_EXTI13_GPIO_Port, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ARD_A5_Pin|ARD_A4_Pin|ARD_A3_Pin|ARD_A2_Pin
                          |ARD_A1_Pin|ARD_A0_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_ANALOG_ADC_CONTROL;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ARD_D1_Pin|ARD_D0_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF8_UART4;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ARD_D10_Pin|SPBTLE_RF_RST_Pin|ARD_D9_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = Bouton3_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING_FALLING;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(Bouton3_GPIO_Port, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ARD_D7_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_ANALOG_ADC_CONTROL;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(ARD_D7_GPIO_Port, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ARD_D13_Pin|ARD_D12_Pin|ARD_D11_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = Bouton2_Pin|Bouton5_Pin|Bouton6_Pin|Bouton4_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING_FALLING;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ISM43362_BOOT0_Pin|ISM43362_WAKEUP_Pin|LED2_Pin|SPSGRF_915_SDN_Pin
                          |SPSGRF_915_SPI3_CSN_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = LPS22HB_INT_DRDY_EXTI0_Pin|LSM6DSL_INT1_EXTI11_Pin|HTS221_DRDY_EXTI15_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = USB_OTG_FS_PWR_EN_Pin|SPBTLE_RF_SPI3_CSN_Pin|PMOD_RESET_Pin|STSAFE_A100_RESET_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = Bouton1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING_FALLING;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(Bouton1_GPIO_Port, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = VL53L0X_XSHUT_Pin|LED3_WIFI__LED4_BLE_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = VL53L0X_GPIO1_EXTI7_Pin|LSM3MDL_DRDY_EXTI8_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = PMOD_SPI2_SCK_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF5_SPI2;
  HAL_GPIO_Init(PMOD_SPI2_SCK_GPIO_Port, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = PMOD_UART2_CTS_Pin|PMOD_UART2_RTS_Pin|PMOD_UART2_TX_Pin|PMOD_UART2_RX_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = ARD_D15_Pin|ARD_D14_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF4_I2C1;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* EXTI interrupt init */
  HAL_NVIC_SetPriority(EXTI0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI0_IRQn);

  HAL_NVIC_SetPriority(EXTI1_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI1_IRQn);

  HAL_NVIC_SetPriority(EXTI2_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI2_IRQn);

  HAL_NVIC_SetPriority(EXTI3_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI3_IRQn);

  HAL_NVIC_SetPriority(EXTI4_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI4_IRQn);

  HAL_NVIC_SetPriority(EXTI9_5_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);

  HAL_NVIC_SetPriority(EXTI15_10_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

void EXTI0_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(Bouton2_Pin);
}

void EXTI1_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(Bouton5_Pin);
}

void EXTI2_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(Bouton6_Pin);
}

void EXTI3_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(Bouton3_Pin);
}

void EXTI4_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(Bouton4_Pin);
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
  int8_t index = Button_GetIndexFromPin(GPIO_Pin);

  if (index < 0)
  {
    return;
  }

  uint32_t now = HAL_GetTick();

  if ((now - g_button_last_irq_tick[index]) < BUTTON_DEBOUNCE_MS)
  {
    return;
  }

  g_button_last_irq_tick[index] = now;

  /*
   * Comme les boutons sont en RISING_FALLING :
   * - falling : appui
   * - rising  : relâchement
   *
   * On prend seulement l'appui réel.
   */
  if (Button_IsPressed((uint8_t)index) != 0U)
  {
    g_button_event_pending[index] = 1U;
  }
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */

  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
