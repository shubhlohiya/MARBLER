<!-- # MARBLER: An Open Platform for Standarized Evaluation of Multi-Robot Reinforcement Learning Algorithms  -->

[Reza J. Torbati](https://github.com/RezaTorbati), 
[Shubham Lohiya](https://shubhlohiya.github.io/),
[Shivika Singh](https://github.com/shivika275),
[Meher S. Nigam](https://github.com/ShashwatNigam99),
[Harish Ravichandar](https://harishravichandar.com/)

[📄 Paper](assets/paper.pdf)   [💻Code](https://github.com/ShashwatNigam99/MARBLER)   [📁Supplementary Material](assets/supplementary.pdf)

## About 

Recent years have seen rapid improvements in Multi-Robot Reinforcement Learning (MRRL). However, many of these novel algorithms have limited real world testing. Although there are several environments for evaluating MRRL algorithms, few of them offer dynamics similar to what real robots experience, and fewer can also test Sim2Real performance. To address these issues, we introduce MARBLER: **M**ulti-**A**gent **R**L **B**enchmark and **L**earning **E**nvironment for the **R**obotarium. MARBLER is a platform built using the Robotarium's simulator that allows for rapid prototyping of new MRRL experiments.

## MARBLER -- Platform Structure

![MARBLER-diag.png](assets/MARBLER-diag.png)

MARBLER comprises several components that form the foundation of the platform:

**Core:** The Core component serves as the fundamental building block of MARBLER, leveraging the Robotarium's python simulator. It encompasses critical functionalities necessary for the environment, such as environment resetting and discrete time step advancement. 

**Scenarios:** The scenarios module defines the environments the robots interact in and the specific tasks they must accomplish. MARBLER offers a collection of pre-defined scenarios, enabling researchers to readily explore various environments. MARBLER also makes it easy for researchers to define their own environments for the Robotarium. 

**Gym Interface:** Each scenario within MARBLER is registered as a Gym environment, allowing direct compatibility with the algorithms and tools that support the OpenAI Gym interface. 

**Test Pipeline:** The Test Pipeline provides a streamlined process for importing trained robots into the simulation environment, allowing visualization of robots performance and collection of test data.

## Results

![res.png](assets/res.png)

We evaluated MAPPO, QMIX, VDN, and QMIX_NS in 4 scenarios using MARBLER. Overall, VDN achieved the best performance across scenarios with QMIX also performing well. The performance of QMIX vs QMIX_NS depended on the heterogeneity of the environment. There were few differences between simulation and real-world performance, highlighting MARBLER's realistic dynamics.

## [Demo](https://www.youtube.com/embed/[placeholder])

<iframe width="560" height="315" src="https://www.youtube.com/embed/[placeholder]" frameborder="0" allowfullscreen></iframe>

## Citation
```
@misc{Torbati2023MARBLER,
  title={MARBLER: An Open Platform for Standardized Evaluation of Multi-Robot Reinforcement Learning Algorithms},
  author={Reza J. Torbati and Shubham Lohiya and Shivika Singh and Meher S. Nigam and Harish Ravichandar},
  journal={arXiv preprint arXiv:2206.XXXXX},
  year={2023}
}
```

## Acknowledgements 
We thank the researchers and staff at the Robotarium for providing access to their simulator and real-world testbed.