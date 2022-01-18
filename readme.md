# Botsorted

Botsorted is a general purpose hosting application I'm using for hosting machine learning models and automated bots.

## Main use

It's currently centred around using machine learning to implement quantitative trading strategies.
Although the application is undergoing a major re-work to make it more scalable, maintainable and more generically applicable to differing trading strategies, there is currently one implemented learning agent still running live.

### **Direct Reinforcement** learning

The only agent currently running live on this application is an implementation of an autoregrssive **Direct Reinforcement** model [(Koker & Koutmos 2020)](https://www.researchgate.net/publication/343565079_Cryptocurrency_Trading_Using_Machine_Learning) to trade bitcoin. 

The actual model in use was estimated using a large grid search of the parameters specified in this paper and using historical bitcoin price data available from coindesk. In order to take advantage of the models ability to take short positions it trades on the Binance futures exchange.

Current performance of the live model (*Reggie 2.0*) can be found [here](http://botsorted.herokuapp.com/getPerformance).


### Maintenance

This is a very old personal app that hasn't been maintained (owing to it being for pure personal use), or have a proper unit testing suite (one of the reasons it's going through a major re-write). I hope to make it more extendible in the next version.


## References

1. [Thomas E. Koker & Dimitrios Koutmos, 2020. "Cryptocurrency Trading Using Machine Learning," JRFM, MDPI, vol. 13(8), pages 1-7, August.](https://www.researchgate.net/publication/343565079_Cryptocurrency_Trading_Using_Machine_Learning)